int limit_dc_motor_speed(int speed, int max=255){
  if(speed>max){return max;}
  if(speed<-max){return -max;}
  return speed;
}

volatile int bl_last_pwm_output = 0;

void init_wheel_motor_pins(){
  for (int i = 0; i < 4; i++) {
    pinMode(wheel_pwm_pin[i][0], OUTPUT);
    pinMode(wheel_pwm_pin[i][1], OUTPUT);
    pinMode(wheel_pwm_pin[i][2], OUTPUT);
    digitalWrite(wheel_pwm_pin[i][0], LOW);
    digitalWrite(wheel_pwm_pin[i][1], LOW);
    analogWrite(wheel_pwm_pin[i][2], 0);
  }
}

// wheel_id FR:0, FL:1, BR:2, BL:3
int cal_pid(int8_t wheel_id){
  float error = wheel_cmd[wheel_id] - wheel_speed[wheel_id];

  wheel_integral[wheel_id] += (error * cal_base_timmer_sec);
  if(wheel_integral[wheel_id] > 100){
    wheel_integral[wheel_id] = 100.0;
  }
  else if(wheel_integral[wheel_id] < -100){
    wheel_integral[wheel_id] = -100.0;
  }

  wheel_derivative[wheel_id] = (error - wheel_pre_error[wheel_id] ) / cal_base_timmer_sec;

  int pwm_output = (wheel_pid_config[wheel_id][0] * error) + 
                   (wheel_pid_config[wheel_id][1] * wheel_integral[wheel_id]) +
                   (wheel_pid_config[wheel_id][2] * wheel_derivative[wheel_id]);
  
  return limit_pmw(pwm_output);
}

void cmd_pwm_motor(uint8_t pin_a, uint8_t pin_b, uint8_t pin_pwm,int pwm_power){
  pwm_power = limit_dc_motor_speed(pwm_power);
  int pwm_output = abs(pwm_power);

  if (pin_a == wheel_BL_in_A_pin && pin_b == wheel_BL_in_B_pin && pin_pwm == wheel_BL_pwm_pin) {
    bl_last_pwm_output = pwm_output;
  }

  if(pwm_power < 0){
    digitalWrite(pin_a, 0);
    digitalWrite(pin_b, 1);
    analogWrite(pin_pwm, pwm_output);
  }
  else if(pwm_power > 0){
    digitalWrite(pin_a, 1);
    digitalWrite(pin_b, 0);
    analogWrite(pin_pwm, pwm_output);
  }
  else{
    digitalWrite(pin_a, 1);
    digitalWrite(pin_b, 1);
    analogWrite(pin_pwm, 0);
  }
}

void debug_bl_wheel(){
  static unsigned long last_bl_debug_ms = 0;
  unsigned long now_ms = millis();
  if (now_ms - last_bl_debug_ms >= 200) {
    last_bl_debug_ms = now_ms;
    Serial.print("BL cmd:");
    Serial.print(wheel_cmd[3], 1);
    Serial.print(" A2:");
    Serial.print(digitalRead(wheel_BL_in_A_pin));
    Serial.print(" B30:");
    Serial.print(digitalRead(wheel_BL_in_B_pin));
    Serial.print(" PWM22:");
    Serial.println(bl_last_pwm_output);
  }
}
