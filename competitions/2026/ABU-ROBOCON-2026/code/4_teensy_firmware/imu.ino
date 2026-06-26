/*void imu_initing(){
  while(r1_imu.beginSPI(imu_cs, imu_int, imu_rst, 1000000, SPI1) == false){
    Serial.println("not detected IMU, Check Wiring now!!!!");
    digitalWrite(13, HIGH); 
    delay(200);
    digitalWrite(13, LOW); 
    delay(200);
  }

  Serial.println("detected IMU");
  delay(500);
  imu_set_report();

}

void imu_set_report(void){
  Serial.println("Setting desired reports");
  if (r1_imu.enableRotationVector() == true) {
    Serial.println(F("Rotation vector enabled"));
    Serial.println(F("Output in form i, j, k, real, accuracy"));
  } else {
    Serial.println("Could not enable rotation vector");
  }
  delay(1000); // This delay allows enough time for the BNO086 to accept the new 
              // configuration and clear its reset status
}


void imu_get_value(){
  if(r1_imu.wasReset()){
    Serial.println("sensor was reset");
    imu_set_report();
  }    

  if(r1_imu.getSensorEvent() == true){
    if (r1_imu.getSensorEventID() == SENSOR_REPORTID_ROTATION_VECTOR) {
      imu_quat_x = r1_imu.getQuatI();
      imu_quat_y = r1_imu.getQuatJ();
      imu_quat_z = r1_imu.getGameQuatK();
      imu_quat_w = r1_imu.getGameQuatReal();

      //imu_euler_x = (r1_imu.getRoll()) - 180.0 / PI;
      //imu_euler_y = (r1_imu.getPitch()) - 180.0 / PI;
      imu_euler_z = r1_imu.getYaw() * 180 / PI;

      Serial.print(imu_quat_x);
      Serial.print(F(","));
      Serial.print(imu_quat_y);
      Serial.print(F(","));
      Serial.print(imu_quat_z);
      Serial.print(F(","));
      Serial.print(imu_quat_w);
      Serial.print(F(","));
      Serial.print(imu_euler_z);

      Serial.println();
    }
  }
}*/