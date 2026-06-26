//#include "SparkFun_BNO08x_Arduino_Library.h"
//#include <QNEthernet.h>
#include "QuadEncoder.h"
// ENCODER_OPTIMIZE_INTERRUPTS removed: restricted pin table silently breaks Encoder.h on pins 16/17.
// Standard attachInterrupt() (default without this define) works on all Teensy 4.1 pins.
#include <Encoder.h>
#include <Servo.h>

#include <micro_ros_arduino.h>
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <std_msgs/msg/float32_multi_array.h>
#include <std_msgs/msg/float32.h>
#include <std_msgs/msg/int8_multi_array.h>
#include <std_msgs/msg/int8.h>
#include <sensor_msgs/msg/imu.h>

//using namespace qindesign::network;

#define imu_cs 39
#define imu_int 40
#define imu_rst 41

// #define wheel_FR_encoder_A_pin 3
// #define wheel_FR_encoder_B_pin 2
#define wheel_FR_in_A_pin 6
#define wheel_FR_in_B_pin 0
#define wheel_FR_pwm_pin 8

#define wheel_FL_encoder_A_pin 27
#define wheel_FL_encoder_B_pin 38
#define wheel_FL_in_A_pin 9
#define wheel_FL_in_B_pin 10
#define wheel_FL_pwm_pin 11

#define wheel_BR_encoder_A_pin 38
#define wheel_BR_encoder_B_pin 26  // pin 7 repurposed as arm_kfs_limit_sw_z_top; encoders unused
#define wheel_BR_in_A_pin 12
#define wheel_BR_in_B_pin 14
#define wheel_BR_pwm_pin 15

#define wheel_BL_encoder_A_pin 31
#define wheel_BL_encoder_B_pin 33
#define wheel_BL_in_A_pin 2
#define wheel_BL_in_B_pin 30
#define wheel_BL_pwm_pin 22

#define arm_kfs_Z_encoder_A_pin 16
#define arm_kfs_Z_encoder_B_pin 17
#define arm_kfs_Z_pwm 24
#define arm_kfs_Z_dir 23

#define arm_kfs_Y_in_A_pin 32  // INA
#define arm_kfs_Y_in_B_pin 28  // INB
#define arm_kfs_Y_pwm_pin  29  // PWM (pin 29 is PWM-capable on Teensy 4.1)

#define arm_kfs_limit_sw_z     25  // lower Z / home    (NC to GND + INPUT_PULLUP: 0=normal, 1=at limit)
#define arm_kfs_limit_sw_z_top  7  // upper Z / stopper (repurposed from wheel_BR_encoder_B; same wiring)
#define arm_kfs_limit_sw_y_out  4  // Y-axis OUT  / extend  limit (repurposed from wheel_FL_encoder_A)
#define arm_kfs_limit_sw_y_in   5  // Y-axis IN   / retract / stored-inside limit (repurposed from wheel_FL_encoder_B)

#define Emergency_pin 34

#define sw_reset_imu 35
#define sw_reset_arm_z 36
#define sw_init_esc 37


#define ESP_SERIAL Serial5

                             //    kp   ki   kd
float wheel_pid_config[4][3] =   {{0.2, 0.1, 0.2},  // FR  wheel
                                  {0.2, 0.1, 0.2},  // FL 
                                  {0.2, 0.1, 0.2},  // BR 
                                  {0.2, 0.1, 0.2}}; // BL

float arm_kfs_config[3] = {15.2,0.0,7.3}; // kp ki kd

int32_t cal_base_timmer = 30000; // time to cal wheel velocity in micro second
float cal_base_timmer_sec = cal_base_timmer / 1000000.0;
int32_t sent_cmd_esp_timer = 40000;
uint16_t encoder_ppr = 1000; // base drive ppr

uint16_t encoder_arm_ksf_ppr = 1000;

byte mac[] = { 0x04, 0xE9, 0xE5, 0x29, 0x06, 0x69 };
IPAddress teensy_ip(192, 168, 0, 12);                 // IP Address Teensy
IPAddress subnet(255, 255, 255, 0);                  
IPAddress gateway(192, 168, 0, 1);
IPAddress pc_ip(192, 168, 0, 2);                // IP Address r1_mini_pc

const uint localPort = 8888;  // Port สำหรับ "รับ" ข้อมูล


float imu_quat_x = 0.0;
float imu_quat_y = 0.0;
float imu_quat_z = 0.0;
float imu_quat_w = 0.0;

float imu_quat_x_adjust = 0.0;
float imu_quat_y_adjust = 0.0;
float imu_quat_z_adjust = 0.0;
float imu_quat_w_adjust = 0.0;

//float imu_euler_x = 0.0;
//float imu_euler_y = 0.0;
float imu_euler_z = 0.0;

//                          FR, FL, BR, BL
int32_t wheel_raw[4]  =    {0,  0,  0,  0};  
int32_t wheel_pre_raw[4] = {0,  0,  0,  0}; 
float wheel_rad[4]    =    {0.0,0.0,0.0,0.0};  // on rad 
float wheel_speed[4]  =    {0.0,0.0,0.0,0.0};  // on rad / s
float wheel_cmd[4]    =    {0.0,0.0,0.0,0.0};
float wheel_integral[4] =  {0.0,0.0,0.0,0.0};
float wheel_derivative[4] ={0.0,0.0,0.0,0.0};
float wheel_pre_error[4] = {0.0,0.0,0.0,0.0};
uint8_t wheel_pwm_pin[4][3] = {{wheel_FR_in_A_pin, wheel_FR_in_B_pin, wheel_FR_pwm_pin},
                                {wheel_FL_in_A_pin, wheel_FL_in_B_pin, wheel_FL_pwm_pin},
                                {wheel_BR_in_A_pin, wheel_BR_in_B_pin, wheel_BR_pwm_pin},
                                {wheel_BL_in_A_pin, wheel_BL_in_B_pin, wheel_BL_pwm_pin}};
float arm_kfs_dis[1]   = {0.0};  // arm Z extent in cm from home
float arm_kfs_cmd[4]   = {0.0,0.0,0.0,0.0};

uint8_t weapon_arm_cmd[2] = {0,0};  // [0]=L_gripper, [1]=L_motor


unsigned long start_time = 0;




//BNO08x r1_imu;
//QuadEncoder encoder_base_FR(1, wheel_FR_encoder_A_pin, wheel_FR_encoder_B_pin, 0);
//QuadEncoder encoder_base_FL(2, wheel_FL_encoder_A_pin, wheel_FL_encoder_B_pin, 0);
//QuadEncoder encoder_base_BR(3, wheel_BR_encoder_A_pin, wheel_BR_encoder_B_pin, 0);
//QuadEncoder encoder_base_BL(4, wheel_BL_encoder_A_pin, wheel_BL_encoder_B_pin, 0);
Encoder arm_kfs_encoder_z(arm_kfs_Z_encoder_A_pin,arm_kfs_Z_encoder_B_pin);

IntervalTimer wheel_speed_timer;
IntervalTimer esp_cmd_timer;
Servo esc_pwm;
Servo esc_dir;

// micro ros setup
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
rcl_timer_t timer_pub;

rcl_publisher_t pub_wheel_state;
rcl_subscription_t sub_wheel_cmd;
std_msgs__msg__Float32MultiArray msg_wheel_state;
std_msgs__msg__Float32MultiArray msg_wheel_cmd;
float array_wheel_state[13];  // [8]=sw_z_bottom(pin25), [9]=sw_z_top(pin7), [10]=Z raw encoder count, [11]=sw_y_out(pin4), [12]=sw_y_in(pin5)
float array_wheel_cmd[4];

rcl_publisher_t pub_imu;
sensor_msgs__msg__Imu msg_imu;
rcl_timer_t timer_imu;

rcl_subscription_t sub_arm_kfs;
std_msgs__msg__Float32MultiArray msg_arm_kfs;
float array_arm_kfs[4];

rcl_subscription_t sub_weapon_arm;
std_msgs__msg__Int8MultiArray msg_weapon_arm;
int8_t array_weapon_arm[2];

rcl_subscription_t sub_current_zone;
std_msgs__msg__Int8 msg_current_zone;
int8_t current_zone = 0;

rcl_publisher_t pub_weapon_angle_state;
std_msgs__msg__Float32MultiArray msg_weapon_angle_state;
float array_weapon_angle_state[3];  // [0]=current_angle, [1]=target_angle, [2]=weapon_angle_power

rcl_subscription_t sub_weapon_angle;
std_msgs__msg__Float32 msg_weapon_angle;   // /weapon_angle_cmd → as5600_target_angle

// sub_weapon_pid_config and sub_weapon_angle_control removed: micro-ros-arduino subscriber limit is 5.
// PID gains tuned at compile time in as5600_control.ino. PID enabled at boot (pid_enabled=true).


//#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){error_loop();}}
#define RCCHECK(fn) { \
  rcl_ret_t temp_rc = fn; \
  if((temp_rc != RCL_RET_OK)){ \
    Serial.print("Micro-ROS Error on line: "); \
    Serial.print(__LINE__); \
    Serial.print(" | Error Code: "); \
    Serial.println((int)temp_rc); \
    error_loop(); \
  } \
}
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){}}

int limit_pmw(int power, int max=255){
  if(power > max){return max;}
  if(power < -max){return -max;}
  return power;
}

void setup() {
  pinMode(13, OUTPUT);
  pinMode(Emergency_pin,INPUT);
  pinMode(sw_reset_imu,INPUT_PULLUP);
  pinMode(sw_reset_arm_z,INPUT_PULLUP);
  pinMode(sw_init_esc,INPUT_PULLUP);
  pinMode(arm_kfs_limit_sw_z,     INPUT_PULLUP);  // lower Z / home
  pinMode(arm_kfs_limit_sw_z_top, INPUT_PULLUP);  // upper Z / stopper

  init_wheel_motor_pins();
  init_esc(); // ESC gets 1000us neutral immediately at boot, before any delays
  // Wait for operator to press sw_init_esc (pin 37) before homing
  // ESC is already armed (receiving neutral) during this wait
  // INPUT_PULLUP: not pressed = HIGH(1), pressed(to GND) = LOW(0)
  //while (digitalRead(sw_init_esc) != 0) {
  //  digitalWrite(13, !digitalRead(13));
  //  delay(300);
  //}
  Serial.begin(115200);  // start serial after ESC gets its signal
  init_as5600();  // AS5600 I2C encoder (SDA=18, SCL=19); moved after Serial.begin so boot log is visible
  //imu_initing();
  init_encoder();
  // Y limit switch pinModes set AFTER init_encoder() to prevent QuadEncoder channel 2
  // (hardware ENC2 on Teensy 4.1, physically tied to pins 4/5) from overriding INPUT_PULLUP
  pinMode(arm_kfs_limit_sw_y_out, INPUT_PULLUP);  // Y OUT / extend limit (pin 4)
  pinMode(arm_kfs_limit_sw_y_in,  INPUT_PULLUP);  // Y IN  / retract / stored limit (pin 5)

  digitalWrite(13, HIGH);
  delay(3000);

  digitalWrite(13, LOW);
     delay(500);

  while(!Serial && millis() < 3000){
     set_esc_zero();
     digitalWrite(13, HIGH);
     delay(500);
     digitalWrite(13, LOW);
     delay(500);
  }
  digitalWrite(13, HIGH);
  print_as5600_boot_info();   // USB now established — print values saved during init_as5600()


  delay(3500);

  Serial.println("Starting micro-ROS setup...");
  
  // Auto-home ArmKFS_Z: drive downward slowly until limit switch or 5s timeout
  // NC switch to GND + INPUT_PULLUP: unpressed=0 (closed to GND), pressed=1 (open, pullup active)
  Serial.println("Homing skipped at boot — will run from Zone 0 behavior tree on PC.");

  Serial.println("Network initialized. Starting micro-ROS...");
  init_micro_ros(false); // false=serial, true=udp
  setup_micro_ros();
  Serial.println("micro-ROS setup successful!");
  init_cmd_esp();

  wheel_speed_timer.begin(cal_wheel_speed, cal_base_timmer);
  esp_cmd_timer.begin(send_cmd_to_esp32,sent_cmd_esp_timer);
}

bool is_button_config = false;
void loop() {
  delay(10);
  digitalWrite(13, HIGH);
  cal_arm_kfs_extend();
  update_angle_control();   // parse W state packets from ESP32 → weapon_angle_power
  debug_bl_wheel();
  RCSOFTCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(20)));

}
