// ============================================================
//  as5600_control.ino  (relay-only — PID moved to ESP32)
//
//  Teensy responsibilities:
//    - as5600_target_angle : set by /weapon_angle_cmd ROS callback
//    - Send G,<target>\n to ESP32 (from connect_to_esp.ino send_cmd_to_esp32)
//    - Parse W,<cur>,<tgt>,<pwr>\n from ESP32 → update weapon_angle_power + _esp_current
//    - Expose getAdjustedAngle() + weapon_angle_power for /weapon_angle_state publisher
//
//  All PID, continuous-angle tracking, zero-offset calibration, and
//  EMA smoothing now live on ESP32 (esp_v2.ino).
// ============================================================

// ── SHARED STATE — read by connect_to_pc.ino wheel_cmd_callback ──
float as5600_target_angle = 0.0f;   // [deg] set by weapon_angle_sub_callback
float weapon_angle_power  = 0.0f;   // received from ESP32 W packet [2]

// ── PRIVATE STATE ──
static float   _esp_current = 0.0f;  // current adjusted angle echoed by ESP32
static char    _w_buf[48];
static uint8_t _w_pos = 0;

// ── Parse W,<cur>,<tgt>,<pwr>\n packets received from ESP32 via Serial5 ──
static void parse_esp32_W_serial() {
    while (ESP_SERIAL.available()) {
        char c = (char)ESP_SERIAL.read();
        if (c == '\n') {
            _w_buf[_w_pos] = '\0';
            if (_w_buf[0] == 'W' && _w_buf[1] == ',') {
                float cur, tgt, pwr;
                if (sscanf(_w_buf + 2, "%f,%f,%f", &cur, &tgt, &pwr) == 3) {
                    _esp_current       = cur;
                    weapon_angle_power = pwr;
                    static unsigned long _dbg_ms = 0;
                    if (millis() - _dbg_ms >= 200) {
                        _dbg_ms = millis();
                        Serial.print("DBG_T_W cur:"); Serial.print(cur, 2);
                        Serial.print(" tgt:"); Serial.print(tgt, 2);
                        Serial.print(" pwr:"); Serial.println(pwr, 1);
                    }
                }
            }
            _w_pos = 0;
        } else if (_w_pos < (uint8_t)(sizeof(_w_buf) - 1)) {
            _w_buf[_w_pos++] = c;
        } else {
            _w_pos = 0;  // overflow — resync
        }
    }
}

// Thin wrapper — called by connect_to_pc.ino wheel_cmd_callback
// Returns current adjusted angle as reported by ESP32.
float getAdjustedAngle() { return _esp_current; }

// No-op stub: zero calibration is now handled by ESP32 at boot using HOME_RAW_ANGLE.
// Teensy cannot override ESP32's zero offset. Restart ESP32 to re-home.
void set_angle_zero() {
    Serial.println("[AS5600] set_angle_zero: no-op (PID on ESP32). Restart ESP32 to re-home.");
}

void print_as5600_boot_info() {
    Serial.println("[AS5600] PID moved to ESP32. Teensy: relay only.");
    Serial.print  ("[AS5600] Initial target sent to ESP32: ");
    Serial.println(as5600_target_angle, 2);
}

void init_as5600() {
    ESP_SERIAL.begin(115200);  // init_cmd_esp() calls begin() again — harmless
    Serial.println("[AS5600] Relay mode: will parse W packets from ESP32.");
}

void update_angle_control() {
    parse_esp32_W_serial();   // drain Serial5 for W state packets from ESP32
    // /weapon_angle_state published in wheel_cmd_callback via getAdjustedAngle()
    // G,<target> sent from send_cmd_to_esp32() in connect_to_esp.ino
}
