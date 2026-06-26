void init_micro_ros(bool use_udp){
  if (use_udp == true){
    set_microros_native_ethernet_udp_transports(mac, teensy_ip, pc_ip, localPort);
  }
  else{set_microros_transports();}
}

char imu_frame_id[] = "imu";
void setup_micro_ros(){
  allocator = rcl_get_default_allocator();
  //create init_options
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

  // create node
  RCCHECK(rclc_node_init_default(&node, "micro_ros_Teensy_node", "", &support));

  // create publishers (3 total — within RMW_UXRCE_MAX_PUBLISHERS limit)
  RCCHECK(rclc_publisher_init_default(&pub_wheel_state,
                                      &node,
                                      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
                                      "teensy/wheel_state"));
    msg_wheel_state.data.capacity = 13;
    msg_wheel_state.data.size = 13;
    msg_wheel_state.data.data = array_wheel_state;

  RCCHECK(rclc_publisher_init_default(&pub_imu,
                                      &node,
                                      ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu),
                                      "Imu_robot"));
    msg_imu.header.frame_id.data = imu_frame_id;
    msg_imu.header.frame_id.size = strlen(imu_frame_id);
    msg_imu.header.frame_id.capacity = msg_imu.header.frame_id.size + 1;

  RCCHECK(rclc_publisher_init_default(&pub_weapon_angle_state,
                                      &node,
                                      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
                                      "weapon_angle_state"));
    msg_weapon_angle_state.data.capacity = 3;
    msg_weapon_angle_state.data.size = 3;
    msg_weapon_angle_state.data.data = array_weapon_angle_state;

  // create subscribers (5 total — at RMW_UXRCE_MAX_SUBSCRIBERS=5 limit)
  // sub_weapon_pid_config and sub_weapon_angle_control removed to stay within limit.
  RCCHECK(rclc_subscription_init_best_effort(&sub_wheel_cmd,
                                          &node,
                                          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
                                          "teensy/wheel_cmd"));
    msg_wheel_cmd.data.capacity = 4;
    msg_wheel_cmd.data.size = 0;
    msg_wheel_cmd.data.data = array_wheel_cmd;

  RCCHECK(rclc_subscription_init_default(&sub_arm_kfs,
                                          &node,
                                           ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
                                           "arm_kfs_cmd"));
    msg_arm_kfs.data.capacity = 4;
    msg_arm_kfs.data.size = 0;
    msg_arm_kfs.data.data = array_arm_kfs;

  RCCHECK(rclc_subscription_init_default(&sub_weapon_arm,
                                          &node,
                                          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int8MultiArray),
                                          "weapon_pos"));
    msg_weapon_arm.data.capacity = 2;
    msg_weapon_arm.data.size = 0;
    msg_weapon_arm.data.data = array_weapon_arm;

  RCCHECK(rclc_subscription_init_default(&sub_current_zone,
                                          &node,
                                          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int8),
                                          "r1_current_zone"))

  RCCHECK(rclc_subscription_init_default(&sub_weapon_angle,
                                          &node,
                                          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
                                          "weapon_angle_cmd"))

  // create timers
  const unsigned int timer_timeout = 50;
  RCCHECK(rclc_timer_init_default(&timer_pub,
                                  &support,
                                  RCL_MS_TO_NS(timer_timeout),
                                  wheel_cmd_callback));

  RCCHECK(rclc_timer_init_default(&timer_imu,
                                  &support,
                                  RCL_MS_TO_NS(20),
                                  imu_timer_callback));

  // create executor (2 timers + 5 subs = 7 entries; 9 slots for safety)
  RCCHECK(rclc_executor_init(&executor, &support.context, 9, &allocator));

  RCCHECK(rclc_executor_add_timer(&executor, &timer_pub));
  RCCHECK(rclc_executor_add_subscription(&executor, &sub_wheel_cmd, &msg_wheel_cmd, &wheel_sub_callback, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_timer(&executor, &timer_imu));
  RCCHECK(rclc_executor_add_subscription(&executor, &sub_arm_kfs, &msg_arm_kfs, &arm_sub_callback, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(&executor, &sub_weapon_arm, &msg_weapon_arm, &weapon_arm_sub_callback, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(&executor, &sub_current_zone, &msg_current_zone, &zone_sub_callback, ON_NEW_DATA))
  RCCHECK(rclc_executor_add_subscription(&executor, &sub_weapon_angle, &msg_weapon_angle, &weapon_angle_sub_callback, ON_NEW_DATA))
}

// function callback
void error_loop(){ // led error status
  while(1){
    digitalWrite(13, !digitalRead(13));
    delay(100);
  }
}

// -- micro-ROS Callbacks --
void wheel_cmd_callback(rcl_timer_t * timer, int64_t last_call_time)
{
  RCLC_UNUSED(last_call_time);
  if (timer != NULL) {
    for(int i=0; i<4; i++){
        msg_wheel_state.data.data[i] =  wheel_cmd[i];
        msg_wheel_state.data.data[i+4] = wheel_speed[i];
    }
    msg_wheel_state.data.data[7] = arm_kfs_dis[0];
    msg_wheel_state.data.data[6] = (float)power;
    msg_wheel_state.data.data[5] = arm_kfs_cmd[0];
    msg_wheel_state.data.data[8]  = (float)digitalRead(arm_kfs_limit_sw_z);      // pin 25: 1=bottom limit hit
    msg_wheel_state.data.data[9]  = (float)digitalRead(arm_kfs_limit_sw_z_top);  // pin 7:  1=top limit hit
    msg_wheel_state.data.data[10] = (float)arm_kfs_encoder_z.read();             // raw count
    msg_wheel_state.data.data[11] = (float)digitalRead(arm_kfs_limit_sw_y_out); // pin 4: 1=OUT limit hit
    msg_wheel_state.data.data[12] = (float)digitalRead(arm_kfs_limit_sw_y_in);  // pin 5: 1=IN limit hit
    RCSOFTCHECK(rcl_publish(&pub_wheel_state, &msg_wheel_state, NULL));

    array_weapon_angle_state[0] = getAdjustedAngle();
    array_weapon_angle_state[1] = as5600_target_angle;
    array_weapon_angle_state[2] = weapon_angle_power;
    RCSOFTCHECK(rcl_publish(&pub_weapon_angle_state, &msg_weapon_angle_state, NULL));
  }
}

void wheel_sub_callback(const void * msgin)
{
  const std_msgs__msg__Float32MultiArray * msg = (const std_msgs__msg__Float32MultiArray *)msgin;

  if(msg->data.size >= 4){
    for(int i = 0; i < 4; i++){
      wheel_cmd[i] = msg->data.data[i];
    }
  }
}

void imu_timer_callback(rcl_timer_t * timer, int64_t last_call_time)
{
  RCLC_UNUSED(last_call_time);
  if (timer != NULL) {
    msg_imu.orientation.x = imu_quat_x;
    msg_imu.orientation.y = imu_quat_y;
    msg_imu.orientation.z = imu_quat_z;
    msg_imu.orientation.w = imu_quat_w;
    RCSOFTCHECK(rcl_publish(&pub_imu, &msg_imu, NULL));
  }
}

void arm_sub_callback(const void * msgin)
{
  const std_msgs__msg__Float32MultiArray * msg = (const std_msgs__msg__Float32MultiArray *)msgin;

  if(msg->data.size >= 4){
    for(int i = 0; i < 4; i++){
      arm_kfs_cmd[i] = msg->data.data[i];
    }
    static unsigned long last_arm_rx_debug_ms = 0;
    unsigned long now_ms = millis();
    if (now_ms - last_arm_rx_debug_ms >= 250) {
      last_arm_rx_debug_ms = now_ms;
      Serial.print("RX arm_kfs_cmd size:");
      Serial.print(msg->data.size);
      Serial.print(" [");
      Serial.print(arm_kfs_cmd[0], 1);
      Serial.print(", ");
      Serial.print(arm_kfs_cmd[1], 1);
      Serial.print(", ");
      Serial.print(arm_kfs_cmd[2], 1);
      Serial.print(", ");
      Serial.print(arm_kfs_cmd[3], 1);
      Serial.println("]");
    }
  }
}

void weapon_arm_sub_callback(const void * msgin)
{
  const std_msgs__msg__Int8MultiArray * msg = (const std_msgs__msg__Int8MultiArray *)msgin;

  if(msg->data.size >= 2){
    for(int i = 0; i < 2; i++){
      weapon_arm_cmd[i] = msg->data.data[i];
    }
  }
}

void zone_sub_callback(const void * msgin){
  const std_msgs__msg__Int8 * msg = (const std_msgs__msg__Int8 *)msgin;
  current_zone = msg->data;
}

void weapon_angle_sub_callback(const void * msgin){
  const std_msgs__msg__Float32 * msg = (const std_msgs__msg__Float32 *)msgin;
  as5600_target_angle = msg->data;   // degrees 0–360, used by update_angle_control()
}
