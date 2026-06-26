#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Encoder.h>

// ── KeepWeapon rotary encoder + limit switch ──────────────────────────────
// Encoder: E6B2-CWZ1X 1000 PPR, voltage output (push-pull — no pull-ups needed on GPIO 34/35)
// Limit:   NC to GND + INPUT_PULLUP on GPIO 32; triggered = LOW (0 = at home)
#define KW_ENCODER_A_PIN     34
#define KW_ENCODER_B_PIN     35
#define KW_LIMIT_PIN         32
#define KW_LIMIT_ACTIVE_LOW  false  // true = NO+GND+PULLUP (triggered=LOW); false = NC+GND+PULLUP (triggered=HIGH)

// ── Hard safety bounds (compile-time — runtime vars must stay inside these) ──
#define KW_HARD_MIN_ANGLE    0.0f
#define KW_HARD_MAX_ANGLE    280.0f

// ── Encoder geometry ──
#define KW_TICKS_PER_REV     4000    // 1000 PPR × 4 (full quadrature decode via PCNT)
#define KW_DEG_PER_TICK      (360.0f / (float)KW_TICKS_PER_REV)   // 0.09 deg/tick

// ── Homing (fixed — not tunable at runtime) ──
#define KW_HOMING_POWER      30      // motor power during homing (positive = CW = toward home)
#define KW_HOMING_TIMEOUT_MS 5000   // fault if home not found within this time (ms)

// ── Motor direction convention ──
// KW_MOTOR_INVERT true  → positive PID output → negative motor cmd → CCW → increasing angle
// KW_MOTOR_INVERT false → positive PID output → positive motor cmd → CW  → decreasing angle
// CW direction moves weapon toward home (limit switch).  Verify at first test.
#define KW_MOTOR_INVERT      true
// KW_ENCODER_INVERT true → flip encoder count sign so increasing count = increasing angle
#define KW_ENCODER_INVERT    false

// ── UART timeout ──
#define G_TIMEOUT_MS         2000   // ms without G packet → hold current position

// ── Existing hardware pins (unchanged) ──
#define RXD2 16
#define TXD2 17
#define pnumatic_weapon_L_GR_pin 33
#define pnumatic_kfs_gr 25
#define weapon_motor_INT_A_pin 26
#define weapon_motor_INT_B_pin 27
#define weapon_motor_PWM_pin   14
#define neopixel_fr_pin 15
#define neopixel_bk_pin 2
#define neopixel_fr_num_pixels 15
#define neopixel_bk_num_pixels 10

Adafruit_NeoPixel neopixels_fr(neopixel_fr_num_pixels, neopixel_fr_pin, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel neopixels_bk(neopixel_bk_num_pixels, neopixel_bk_pin, NEO_GRB + NEO_KHZ800);

int teensy_cmd[6] = {0,0,0,0,0,0};  // [0]=L_gr [1]=ignored [2]=kfs_gr [3]=kfs_slot [4]=neo_fr [5]=neo_bk

uint8_t color_rgb[6][3] = {{255,0,0},     // red    index 0
                            {255,255,0},  // orange index 1
                            {0,255,0},    // green  index 2
                            {0,0,255},    // blue   index 3
                            {0,255,255},  // cyan   index 4
                            {255,0,255}}; // purple index 5

unsigned long previousMillis = 0;
const long blinkInterval = 300;
bool blinkState = false;

// ── Non-blocking Serial2 receive buffer (Teensy → ESP32) ──
static char    _rx_buf[64];
static uint8_t _rx_pos = 0;

// ── Runtime-tunable controller parameters ────────────────────────────────
// Updated by K packet:  K,<min>,<max>,<kp>,<ki>,<kd>,<maxP>,<minP>,<db>\n
// Defaults match compile-time values used previously.
// Zone angle constants (HOME/ENTRY/ARMED) are owned by the Pi behavior tree,
// not here.  These are safety clamp bounds and PID tuning only.
static float kw_min_angle  = 0.0f;    // runtime soft lower limit (>= KW_HARD_MIN_ANGLE)
static float kw_max_angle  = 280.0f;  // runtime soft upper limit (<= KW_HARD_MAX_ANGLE)
static float kw_kp         = 0.25f;
static float kw_ki         = 0.00f;
static float kw_kd         = 0.02f;
static float kw_max_power  = 25.0f;
static float kw_min_power  = 10.0f;   // stiction boost threshold
static float kw_deadband   = 2.0f;    // degrees

// ── KeepWeapon state machine ──────────────────────────────────────────────
typedef enum { KW_BOOT, KW_HOMING, KW_HOMED, KW_FAULT } kw_state_t;

ESP32Encoder kw_encoder;

static kw_state_t    kw_state        = KW_BOOT;
static float         kw_current      = 0.0f;   // current angle (degrees from home)
static float         kw_target       = 0.0f;   // target angle from G packet
static float         kw_power        = 0.0f;   // last PID output
static int           kw_last_cmd     = 0;       // last cmd sent to motor (for debug)
static bool          kw_target_rcvd  = false;
static unsigned long kw_last_g_ms    = 0;
static unsigned long kw_home_start   = 0;      // timestamp when homing began

// PID integrator state
static float kw_integral = 0.0f;
static float kw_prev_err = 0.0f;

// ── Read angle from encoder ──
static float kw_read_angle() {
    long count = kw_encoder.getCount();
    if (KW_ENCODER_INVERT) count = -count;
    return (float)count * KW_DEG_PER_TICK;
}

// ── Limit switch: returns true when weapon is at home position ──
static bool kw_at_home() {
    int raw = digitalRead(KW_LIMIT_PIN);
    return KW_LIMIT_ACTIVE_LOW ? (raw == LOW) : (raw == HIGH);
}

// ── PID (linear error — no circular math needed for 0–200° range) ──
static float kw_pid_calc(float error, float dt) {
    kw_integral += error * dt;
    if (kw_integral >  100.0f) kw_integral =  100.0f;
    if (kw_integral < -100.0f) kw_integral = -100.0f;
    float deriv   = (error - kw_prev_err) / dt;
    kw_prev_err   = error;
    float out     = kw_kp * error + kw_ki * kw_integral + kw_kd * deriv;
    if (out >  kw_max_power) out =  kw_max_power;
    if (out < -kw_max_power) out = -kw_max_power;
    return out;
}

// ── Send W state packet to Teensy ──
static void send_weapon_state_packet() {
    char buf[48];
    snprintf(buf, sizeof(buf), "W,%.2f,%.2f,%.1f\n", kw_current, kw_target, kw_power);
    Serial2.print(buf);
}

// ── Initialize encoder and limit switch ──
static void kw_init() {
    pinMode(KW_LIMIT_PIN, INPUT_PULLUP);
    kw_encoder.attachFullQuad(KW_ENCODER_A_PIN, KW_ENCODER_B_PIN);
    kw_encoder.setCount(0);
    Serial.println("[KW] Encoder init: A=34 B=35 LIM=32 ticks/rev=4000");
}

// ── Parse K config packet from Teensy ──────────────────────────────────
// Format: K,<min_angle>,<max_angle>,<kp>,<ki>,<kd>,<maxPower>,<minPower>,<deadband>
// Validation: min >= 0, max <= 220, max > min, maxP in [0,100], minP in [0,maxP], db > 0
static void parse_K_packet(const char* data) {
    float min_a, max_a, kp, ki, kd, maxP, minP, db;
    if (sscanf(data, "%f,%f,%f,%f,%f,%f,%f,%f",
               &min_a, &max_a, &kp, &ki, &kd, &maxP, &minP, &db) != 8) {
        Serial.println("[KW_CFG] K parse error: expected 8 fields");
        return;
    }
    // Clamp to hard bounds
    if (min_a < KW_HARD_MIN_ANGLE) min_a = KW_HARD_MIN_ANGLE;
    if (max_a > KW_HARD_MAX_ANGLE) max_a = KW_HARD_MAX_ANGLE;
    // Validate relationships
    if (max_a <= min_a) { Serial.println("[KW_CFG] K rejected: max <= min"); return; }
    if (maxP < 0.0f || maxP > 100.0f) { Serial.println("[KW_CFG] K rejected: maxPower out of range"); return; }
    if (minP < 0.0f || minP > maxP)   { Serial.println("[KW_CFG] K rejected: minPower out of range"); return; }
    if (db <= 0.0f)                    { Serial.println("[KW_CFG] K rejected: deadband <= 0"); return; }
    // Apply
    kw_min_angle = min_a;
    kw_max_angle = max_a;
    kw_kp        = kp;
    kw_ki        = ki;
    kw_kd        = kd;
    kw_max_power = maxP;
    kw_min_power = minP;
    kw_deadband  = db;
    // Reset PID integrator on config change to prevent windup with new gains
    kw_integral  = 0.0f;
    kw_prev_err  = 0.0f;
    Serial.print("[KW_CFG] Applied: min:"); Serial.print(kw_min_angle, 1);
    Serial.print(" max:"); Serial.print(kw_max_angle, 1);
    Serial.print(" kp:"); Serial.print(kw_kp, 3);
    Serial.print(" ki:"); Serial.print(kw_ki, 3);
    Serial.print(" kd:"); Serial.print(kw_kd, 3);
    Serial.print(" maxP:"); Serial.print(kw_max_power, 1);
    Serial.print(" minP:"); Serial.print(kw_min_power, 1);
    Serial.print(" db:"); Serial.println(kw_deadband, 2);
}

// ── Main keepweapon update — 50 Hz ───────────────────────────────────────
static void kw_update() {
    static unsigned long _last_ms    = 0;
    static unsigned long _cfg_dbg_ms = 0;
    static unsigned long _dbg_ms     = 0;
    unsigned long now = millis();

    // DBG_KW: unconditional 200ms print — not gated by 50Hz rate limit
    if (now - _dbg_ms >= 200) {
        _dbg_ms = now;
        int _lim_raw = digitalRead(KW_LIMIT_PIN);
        int _a_raw   = digitalRead(KW_ENCODER_A_PIN);
        int _b_raw   = digitalRead(KW_ENCODER_B_PIN);
        bool _lim = kw_at_home();
        const char* _ss = (kw_state == KW_BOOT)   ? "BOOT"   :
                          (kw_state == KW_HOMING) ? "HOMING" :
                          (kw_state == KW_HOMED)  ? "HOMED"  : "FAULT";
        Serial.print("DBG_KW enc:"); Serial.print(kw_encoder.getCount());
        Serial.print(" cur:"); Serial.print(kw_current, 2);
        Serial.print(" a:"); Serial.print(_a_raw);
        Serial.print(" b:"); Serial.print(_b_raw);
        Serial.print(" tgt:"); Serial.print(kw_target, 2);
        Serial.print(" err:"); Serial.print(kw_target - kw_current, 1);
        Serial.print(" pwr:"); Serial.print(kw_power, 1);
        Serial.print(" cmd:"); Serial.print(kw_last_cmd);
        Serial.print(" home:"); Serial.print(kw_state == KW_HOMED ? 1 : 0);
        Serial.print(" lim_raw:"); Serial.print(_lim_raw);
        Serial.print(" lim:"); Serial.print(_lim ? 1 : 0);
        Serial.print(" fault:"); Serial.print(kw_state == KW_FAULT ? 1 : 0);
        Serial.print(" state:"); Serial.println(_ss);
    }

    // Rate-limit state machine to 50Hz
    if (now - _last_ms < 20) return;
    _last_ms = now;

    kw_current  = kw_read_angle();
    bool at_lim = kw_at_home();

    switch (kw_state) {

    // ── BOOT: check if already at home, decide whether to home ──
    case KW_BOOT:
        control_weapon_motor(0);
        if (at_lim) {
            kw_encoder.setCount(0);
            kw_current = 0.0f;
            kw_target  = 0.0f;
            kw_state   = KW_HOMED;
            Serial.println("[KW] Boot: already at limit — skip homing.");
        } else {
            kw_home_start = now;
            kw_state      = KW_HOMING;
            Serial.println("[KW] Boot: not at limit — homing...");
        }
        break;

    // ── HOMING: drive CW (positive cmd) until limit switch triggers ──
    case KW_HOMING:
        if (at_lim) {
            control_weapon_motor(0);
            kw_encoder.setCount(0);
            kw_current  = 0.0f;
            kw_target   = 0.0f;
            kw_integral = 0.0f;
            kw_prev_err = 0.0f;
            kw_state    = KW_HOMED;
            Serial.println("[KW] Homing complete.");
        } else if (now - kw_home_start > KW_HOMING_TIMEOUT_MS) {
            control_weapon_motor(0);
            kw_state = KW_FAULT;
            Serial.println("[KW] Homing TIMEOUT — FAULT.");
        } else {
            control_weapon_motor(KW_HOMING_POWER);
        }
        break;

    // ── HOMED: normal PID position control ──
    case KW_HOMED: {
        if (at_lim) {
            // Always re-zero encoder when limit is active.
            kw_encoder.setCount(0);
            kw_current = 0.0f;

            // If target is at home (within deadband): stop and hold.
            if (kw_target <= kw_deadband) {
                kw_last_cmd = 0;
                control_weapon_motor(0);
                kw_power    = 0.0f;
                kw_integral = 0.0f;
                kw_prev_err = 0.0f;
                send_weapon_state_packet();
                return;
            }
            // Otherwise target is away from home — fall through to PID so
            // the motor can drive away from the limit switch.
        }

        // G timeout: no target received for G_TIMEOUT_MS → hold current position
        if (kw_target_rcvd && (now - kw_last_g_ms > G_TIMEOUT_MS)) {
            kw_target   = kw_current;
            kw_integral = 0.0f;
            kw_prev_err = 0.0f;
        }

        // Clamp target to runtime soft limits
        // (zone angle constants live on the Pi — ESP32 only enforces the safety range)
        float tgt   = constrain(kw_target, kw_min_angle, kw_max_angle);
        float error = tgt - kw_current;

        if (fabsf(error) <= kw_deadband) {
            kw_last_cmd = 0;
            control_weapon_motor(0);
            kw_power    = 0.0f;
            kw_integral = 0.0f;
        } else {
            float output = kw_pid_calc(error, 0.020f);
            // Stiction boost: push past static friction when outside deadband but output is tiny
            if (kw_min_power < kw_max_power &&
                fabsf(output) >= 1.0f &&
                fabsf(output) < kw_min_power &&
                fabsf(error)  > kw_deadband * 2.0f) {
                output = (output > 0.0f) ? kw_min_power : -kw_min_power;
            }
            kw_power = output;
            int cmd = (KW_MOTOR_INVERT ? -1 : 1) * (int)kw_power;
            // Safety: never drive into the limit switch.
            // With KW_MOTOR_INVERT=true: cmd>0 = CW = toward home.
            if (at_lim && cmd > 0) {
                cmd = 0;
            }
            kw_last_cmd = cmd;
            control_weapon_motor(cmd);
        }
        break;
    }

    // ── FAULT: motor off; pressing limit switch clears fault and re-homes ──
    case KW_FAULT:
        control_weapon_motor(0);
        kw_power = 0.0f;
        if (at_lim) {
            kw_encoder.setCount(0);
            kw_current  = 0.0f;
            kw_target   = 0.0f;
            kw_integral = 0.0f;
            kw_prev_err = 0.0f;
            kw_power    = 0.0f;
            kw_state    = KW_HOMED;
            Serial.println("[KW] Fault cleared by limit switch — re-homed.");
        }
        break;
    }

    // Throttled debug: config (every 5 s)
    if (now - _cfg_dbg_ms >= 5000) {
        _cfg_dbg_ms = now;
        Serial.print("DBG_KW_CFG min:"); Serial.print(kw_min_angle, 1);
        Serial.print(" max:"); Serial.print(kw_max_angle, 1);
        Serial.print(" kp:"); Serial.print(kw_kp, 3);
        Serial.print(" ki:"); Serial.print(kw_ki, 3);
        Serial.print(" kd:"); Serial.print(kw_kd, 3);
        Serial.print(" maxP:"); Serial.print(kw_max_power, 0);
        Serial.print(" minP:"); Serial.print(kw_min_power, 0);
        Serial.print(" db:"); Serial.println(kw_deadband, 1);
    }

    send_weapon_state_packet();
}

// ── Process one CSV command line from Teensy (pneumatics + NeoPixel) ──
static void process_teensy_cmd(const char* line) {
    int vals[6];
    int cnt = sscanf(line, "%d,%d,%d,%d,%d,%d",
                     &vals[0], &vals[1], &vals[2], &vals[3], &vals[4], &vals[5]);
    if (cnt == 6) {
        for (int i = 0; i < 6; i++) teensy_cmd[i] = vals[i];
        execute_pneumatics();
        // teensy_cmd[1] ignored — weapon motor is owned by kw_update() PID
    }
}

// ── Dispatch one received line: G target / K config / CSV commands ──
static void parse_teensy_line(const char* line) {
    if (line[0] == 'G' && line[1] == ',') {
        // Target angle from Pi behavior tree via Teensy relay.
        // Zone angle constants (HOME/ENTRY/ARMED) are on the Pi — ESP32 just receives whatever target arrives.
        float t = atof(line + 2);
        if (!isnan(t) && !isinf(t)) {
            kw_target      = constrain(t, kw_min_angle, kw_max_angle);
            kw_last_g_ms   = millis();
            kw_target_rcvd = true;
            static unsigned long _dbg_g = 0;
            if (millis() - _dbg_g >= 2000) {
                _dbg_g = millis();
                Serial.print("DBG_G tgt:"); Serial.println(kw_target, 2);
            }
        }
    } else if (line[0] == 'K' && line[1] == ',') {
        // Controller config packet: K,<min>,<max>,<kp>,<ki>,<kd>,<maxP>,<minP>,<db>
        parse_K_packet(line + 2);
    } else {
        process_teensy_cmd(line);
    }
}

// ── Non-blocking Serial2 receive — call every loop() ──
static void parse_teensy_serial() {
    while (Serial2.available()) {
        char c = (char)Serial2.read();
        if (c == '\n') {
            _rx_buf[_rx_pos] = '\0';
            if (_rx_pos > 0) parse_teensy_line(_rx_buf);
            _rx_pos = 0;
        } else if (_rx_pos < (uint8_t)(sizeof(_rx_buf) - 1)) {
            _rx_buf[_rx_pos++] = c;
        } else {
            _rx_pos = 0;   // overflow — resync
        }
    }
}


void setup() {
    Serial.begin(115200);
    Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2);
    // Wire.begin() removed: no I2C sensors used in this version

    kw_init();   // encoder (PCNT) + limit switch GPIO

    pinMode(pnumatic_weapon_L_GR_pin, OUTPUT);
    pinMode(pnumatic_kfs_gr,          OUTPUT);
    pinMode(weapon_motor_INT_A_pin,   OUTPUT);
    pinMode(weapon_motor_INT_B_pin,   OUTPUT);
    pinMode(weapon_motor_PWM_pin,     OUTPUT);
    pinMode(neopixel_fr_pin,          OUTPUT);
    pinMode(neopixel_bk_pin,          OUTPUT);

    neopixels_fr.begin();
    neopixels_bk.begin();
    neopixels_fr.show();
    neopixels_bk.show();
}

void loop() {
    parse_teensy_serial();   // G target, K config, CSV pneumatics/NeoPixel
    kw_update();             // encoder → PID → motor → W state (50 Hz)
    control_neo_pixel();
}

void execute_pneumatics() {
    digitalWrite(pnumatic_weapon_L_GR_pin, teensy_cmd[0]);  // L gripper
    digitalWrite(pnumatic_kfs_gr,          teensy_cmd[2]);  // KFS gripper
}

void control_weapon_motor(int cmd) {
    // cmd: signed power (-100 to +100)
    //   positive → CW  (INT_A=HIGH, INT_B=LOW) → toward home / decreasing angle
    //   negative → CCW (INT_A=LOW,  INT_B=HIGH) → away from home / increasing angle
    //   zero     → brake
    if (cmd > 0) {
        digitalWrite(weapon_motor_INT_A_pin, HIGH);
        digitalWrite(weapon_motor_INT_B_pin, LOW);
        analogWrite(weapon_motor_PWM_pin, map(cmd, 0, 100, 0, 255));
    } else if (cmd < 0) {
        digitalWrite(weapon_motor_INT_A_pin, LOW);
        digitalWrite(weapon_motor_INT_B_pin, HIGH);
        analogWrite(weapon_motor_PWM_pin, map(-cmd, 0, 100, 0, 255));
    } else {
        digitalWrite(weapon_motor_INT_A_pin, LOW);
        digitalWrite(weapon_motor_INT_B_pin, LOW);
        analogWrite(weapon_motor_PWM_pin, 0);
    }
}

void control_neo_pixel() {
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= blinkInterval) {
        previousMillis = currentMillis;
        blinkState = !blinkState;
    }

    // Front strip (teensy_cmd[4])
    if (teensy_cmd[4] == -1) {
        set_fr_neopixel_color(blinkState ? 255 : 0, 0, 0);
    } else if (teensy_cmd[4] == -2) {
        set_fr_neopixel_color(255, 0, 0);   // solid red
    } else {
        int idx = teensy_cmd[4] + 1;
        if (idx >= 1 && idx < 6)
            set_fr_neopixel_color(color_rgb[idx][0], color_rgb[idx][1], color_rgb[idx][2]);
    }

    // Back strip (teensy_cmd[5])
    if (teensy_cmd[5] == -1) {
        set_bk_neopixel_color(blinkState ? 255 : 0, 0, 0);
    } else if (teensy_cmd[5] == -2) {
        set_bk_neopixel_color(255, 0, 0);   // solid red
    } else {
        int idx = teensy_cmd[5] + 1;
        if (idx >= 1 && idx < 6)
            set_bk_neopixel_color(color_rgb[idx][0], color_rgb[idx][1], color_rgb[idx][2]);
    }
}

void set_fr_neopixel_color(uint8_t r, uint8_t g, uint8_t b) {
    for (int i = 0; i < neopixel_fr_num_pixels; i++)
        neopixels_fr.setPixelColor(i, neopixels_fr.Color(r, g, b));
    neopixels_fr.show();
}

void set_bk_neopixel_color(uint8_t r, uint8_t g, uint8_t b) {
    for (int i = 0; i < neopixel_bk_num_pixels; i++)
        neopixels_bk.setPixelColor(i, neopixels_bk.Color(r, g, b));
    neopixels_bk.show();
}
