// Default KW controller config sent to ESP32 at boot.
// Tune these values here; they will be sent as K packet on power-on.
// Format: K,<min_angle>,<max_angle>,<kp>,<ki>,<kd>,<maxPower>,<minPower>,<deadband>
static void send_kw_config_to_esp32() {
  char k_buf[64];
  // Format: K,<min_angle>,<max_angle>,<kp>,<ki>,<kd>,<maxPower>,<minPower>,<deadband>
  snprintf(k_buf, sizeof(k_buf), "K,0.0,200.0,0.25,0.00,0.02,35.0,20.0,2.0\n");
  ESP_SERIAL.print(k_buf);
}

void init_cmd_esp(){
  ESP_SERIAL.begin(115200);
  delay(200);  // allow ESP32 Serial2 to stabilize before sending config
  send_kw_config_to_esp32();
}

/*  index     cmd           value
      0    weapon_L_gr       0,1
      1    weapon_L_motor   -1,0,1
      2      kfs_gr          0,1
      3      kfs_slot       -1,0,1
      4  neo_pixel_color_fr  0-x
      5  neo_pixel_color_bk  0-x */

uint8_t neo_pixel_fr = 1;
uint8_t neo_pixel_bk = 1;

void send_cmd_to_esp32(){
  char serial_buffer[50];
  cmd_neo_pixel_color();

  // Boot-safe period: force kfs_gripper=0 for the first 50 commands (~2 seconds).
  // Prevents stale BT state (kfs_gripper=1 from previous session) from activating
  // the box gripper immediately after homing completes and Micro-ROS reconnects.
  static uint16_t boot_cmd_count = 0;
  int kfs_gr = (boot_cmd_count < 50) ? 0 : (int)arm_kfs_cmd[2];
  if (boot_cmd_count < 50) boot_cmd_count++;

  snprintf(serial_buffer, sizeof(serial_buffer),"%d,%d,%d,%d,%d,%d\n",
          (int)weapon_arm_cmd[0],      // L gripper
          0,                           // weapon motor: driven by ESP32 local PID (slot ignored)
          kfs_gr,                      // KFS gripper (boot-safe guarded)
          (int)arm_kfs_cmd[3],         // KFS slot
          neo_pixel_fr,
          neo_pixel_bk);
  ESP_SERIAL.print(serial_buffer);

  // Send weapon angle target to ESP32 for its local PID loop
  char g_buf[20];
  snprintf(g_buf, sizeof(g_buf), "G,%.2f\n", as5600_target_angle);
  ESP_SERIAL.print(g_buf);
}

void cmd_neo_pixel_color(){
  if (current_zone == 0){
    neo_pixel_fr = 0;
    neo_pixel_bk = 0;
  }
  else if(current_zone == 1){
    neo_pixel_fr = 1;
    neo_pixel_bk = 1;
  }
  else if(current_zone == 2){
    neo_pixel_fr = 2;
    neo_pixel_bk = 2;
  }
  else if(current_zone == 3){
    neo_pixel_fr = 3;
    neo_pixel_bk = 3;
  }
  else if(current_zone == 5){
    neo_pixel_fr = -2;  // solid red (PS NeoPixel override)
    neo_pixel_bk = -2;
  }
  else{
    neo_pixel_fr = -1;
    neo_pixel_bk = -1;
  }
}