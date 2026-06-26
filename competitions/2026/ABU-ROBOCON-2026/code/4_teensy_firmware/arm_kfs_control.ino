void init_esc(){
  esc_pwm.attach(arm_kfs_Z_pwm,1000,2000);
  esc_dir.attach(arm_kfs_Z_dir,1000,2000);
  set_esc_zero();
  delay(1000);
}

void set_esc_zero(){
  esc_pwm.writeMicroseconds(1000);
  esc_dir.writeMicroseconds(1000);
}

// Hold sw_init_esc (pin 37) to keep re-arming ESC every 1s while held.
void reset_esc_if_btn(){
  static unsigned long last_reset_ms = 0;
  if (digitalRead(sw_init_esc) == LOW) {
    unsigned long now = millis();
    if (now - last_reset_ms >= 1000) {
      last_reset_ms = now;
      esc_pwm.detach();
      esc_dir.detach();
      esc_pwm.attach(arm_kfs_Z_pwm, 1000, 2000);
      esc_dir.attach(arm_kfs_Z_dir, 1000, 2000);
      set_esc_zero();
    }
  }
}


void is_init_arm(){
  if(digitalRead(sw_reset_arm_z) == 1){
    while(digitalRead(arm_kfs_limit_sw_z) != 1){  // NC switch: loop while 0 (away from limit), exit at 1 (hit limit)
      esc_dir.writeMicroseconds(1900);  // direction: downward (verified: 1900=DOWN, 1100=UP)
      esc_pwm.writeMicroseconds(1200);  // slow speed (raised from 1160 to clear deadband)
    }
      set_esc_zero();
      arm_kfs_encoder_z.write(0);
  }
}

 // range 0-100, 0-255
// positive z_pwm = UP (1100), negative z_pwm = DOWN (1900, same as homing)
// z_pwm == 0: true ESC stop (1000µs) — do NOT change direction to avoid pre-biasing UP
void cmd_arm_esc(int z_pwm, int y_percent){
  z_pwm = limit_pmw(z_pwm,100);

  if (z_pwm < 0){
    esc_dir.writeMicroseconds(1900);  // DOWN
    esc_pwm.writeMicroseconds(map(abs(z_pwm),0,100,1125,1450));
  }
  else if (z_pwm > 0){
    esc_dir.writeMicroseconds(1100);  // UP
    esc_pwm.writeMicroseconds(map(z_pwm,0,100,1125,1450));
  }
  else {
    // z_pwm == 0: true stop — esc_dir unchanged (keeps last direction), esc_pwm = 1000
    esc_pwm.writeMicroseconds(1000);
  }

  cmd_pwm_motor(arm_kfs_Y_in_A_pin, arm_kfs_Y_in_B_pin, arm_kfs_Y_pwm_pin, limit_pmw(y_percent));
}

int er=0;
int pre_arm_z_error = 0;
float error = 0;
int power = 0;
void cal_arm_kfs_extend(){
  arm_kfs_dis[0] = arm_kfs_encoder_z.read() * 4.81 / (float)encoder_arm_ksf_ppr; // in cm


  float z_cmd = arm_kfs_cmd[0];

  if (z_cmd >= 50.0) {
    // Direct velocity mode — UP. cmd 50–100 maps to power 40–80.
    // cmd=100 = Zone 0 baseline (power 80). Lower cmd = slower speed.
    error = 0;
    power = (int)map((long)z_cmd, 50L, 100L, 40L, 80L);
  } else if (z_cmd <= -50.0) {
    // Direct velocity mode — DOWN. cmd -50 to -100 maps to power -40 to -80.
    error = 0;
    power = -(int)map((long)(-z_cmd), 50L, 100L, 40L, 80L);
  } else if (z_cmd == 0.0) {
    // Stop command: hold position (no driving).
    error = 0;
    power = 0;
  } else {
    // Position PID mode (used by semi-auto / other zones).
    error = z_cmd - arm_kfs_dis[0];
    power = (int)((error * arm_kfs_config[0]) + ((error - pre_arm_z_error) * arm_kfs_config[2]));
  }

  // Z limit switch protection — always applied, direction-specific.
  // When blocked: also zero error so derivative does not accumulate → prevents jitter.
  int sw_z_bottom = digitalRead(arm_kfs_limit_sw_z);      // pin 25: 1=bottom limit hit
  int sw_z_top    = digitalRead(arm_kfs_limit_sw_z_top);  // pin 7:  1=top limit hit
  if (sw_z_bottom == 1 && power < 0) { power = 0; error = 0; }  // block DOWN, allow UP
  if (sw_z_bottom == 1) { arm_kfs_encoder_z.write(0); }         // auto-zero encoder at home
  if (sw_z_top    == 1 && power > 0) { power = 0; error = 0; }  // block UP,   allow DOWN

  pre_arm_z_error = error;  // updated after limit clamp: keeps derivative baseline clean

  int y_power = 0;
  int sw_y_out = digitalRead(arm_kfs_limit_sw_y_out);  // pin 4: 0=released/normal, 1=pressed/limit
  int sw_y_in  = digitalRead(arm_kfs_limit_sw_y_in);   // pin 5: 0=released/normal, 1=pressed/limit
  if (arm_kfs_cmd[1] >= 0.5  && sw_y_out == 0) { y_power =  (int)constrain(arm_kfs_cmd[1],  1, 100); }
  if (arm_kfs_cmd[1] <= -0.5 && sw_y_in  == 0) { y_power = -(int)constrain(-arm_kfs_cmd[1], 1, 100); }

  // --- Z+Y debug log (every 200ms to avoid Serial spam) ---
  static unsigned long last_z_debug_ms = 0;
  unsigned long now_ms = millis();
  if (now_ms - last_z_debug_ms >= 200) {
    last_z_debug_ms = now_ms;
    long z_raw = arm_kfs_encoder_z.read();
    Serial.print("Z_raw:"); Serial.print(z_raw);
    Serial.print(" Z_pos:");  Serial.print(arm_kfs_dis[0], 2);
    Serial.print("cm Z_cmd:"); Serial.print(arm_kfs_cmd[0], 0);
    Serial.print(" Z_pwr:");  Serial.print(power);
    Serial.print(" Bot(25):"); Serial.print(sw_z_bottom);
    Serial.print(" Top(7):");  Serial.print(sw_z_top);
    Serial.print(" | Y_cmd:"); Serial.print(arm_kfs_cmd[1], 1);
    Serial.print(" Y_pwr:");   Serial.print(y_power);
    Serial.print(" Out(4):"); Serial.print(sw_y_out);
    Serial.print(" In(5):");  Serial.println(sw_y_in);
  }

  cmd_arm_esc(power, y_power);
  er = error;
}


