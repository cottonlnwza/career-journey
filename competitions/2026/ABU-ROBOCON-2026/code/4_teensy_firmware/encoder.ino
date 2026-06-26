void init_encoder(){
  encoder_base_FR.setInitConfig();
  encoder_base_FL.setInitConfig();
  encoder_base_BR.setInitConfig();
  encoder_base_BL.setInitConfig();
  encoder_base_FR.init();
  encoder_base_FL.init();
  encoder_base_BR.init();
  encoder_base_BL.init();
}

void cal_wheel_speed(){
  //start_time = micros();
  wheel_raw[0] = encoder_base_FR.read();
  wheel_raw[1] = encoder_base_FL.read();
  wheel_raw[2] = encoder_base_BR.read();
  wheel_raw[3] = encoder_base_BL.read();

  for(int i=0; i<4; i++){
    wheel_speed[i] = cal_velocity(wheel_raw[i], wheel_pre_raw[i]);
    wheel_pre_raw[i] = wheel_raw[i];
  }

  for (int i=0; i<4; i++){
    //cal_pid(i);
    cmd_pwm_motor(wheel_pwm_pin[i][0],wheel_pwm_pin[i][1],wheel_pwm_pin[i][2], (int)wheel_cmd[i]);//cal_pid(i));
  }
  //Serial.println(micros()-start_time);
}

float cal_velocity(int32_t current, int32_t pre){
  float rad_speed = ((((float)current - (float)pre) / (float)encoder_ppr ) * 2.0 * PI) / cal_base_timmer_sec;
  return rad_speed;
}

