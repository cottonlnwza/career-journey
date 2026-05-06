//1. เช็คสายไฟ + Power Distribution
//2. ตรวจทิศทางมอเตอร์ (Motor Direction Mapping)
//3. เช็ค Limit Switch (แกน X)  HIGH = ยังไม่ชน  LOW = ชนแล้ว
//4. เช็คมอเตอร์แกน Y ว่าทิศถูก
//5. Servo Orientation + Mechanical Load
//6. ทดสอบมุม 0°, 90°, 180° แบบปลอดภัย
// 7. ทดสอบฟังก์ชัน SemiAuto_Y แยกก่อน
//8. ทดสอบ sticks และปุ่มกด ว่าค่าถูกต้อง
#include <ps5Controller.h>

bool toggle[16] = {false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false};

unsigned long previousMillis = 0;
const long interval = 100;

void onConnect() {
  Serial.println("Connected!.");
}

void onDisConnect() {
  Serial.println("Disconnected!.");
}

void onEvent() {
  if(ps5.event.button_down.square) {
    toggle[0] = !toggle[0];
    Serial.print("Square: ");
    Serial.println(toggle[0]);
  }
  if(ps5.event.button_down.triangle) {
    toggle[1] = !toggle[1];
    Serial.print("Triangle: ");
    Serial.println(toggle[1]);
  }
  if(ps5.event.button_down.circle) {
    toggle[2] = !toggle[2];
    Serial.print("Circle: ");
    Serial.println(toggle[2]);
  }

  if(ps5.event.button_down.l1) {
    toggle[4] = !toggle[4];
    Serial.print("L1: ");
    Serial.println(toggle[4]);
  }
  if(ps5.event.button_down.r1) {
    toggle[6] = !toggle[6];
    Serial.print("R1: ");
    Serial.println(toggle[6]);
  }
  if(ps5.event.button_down.share) {
    toggle[8] = !toggle[8];
    Serial.print("Share: ");
    Serial.println(toggle[8]);
  }
  if(ps5.event.button_down.ps) {
    toggle[10] = !toggle[10];
    Serial.print("PS: ");
    Serial.println(toggle[10]);
  }
  if(ps5.event.button_down.touchpad) {
    toggle[11] = !toggle[11];
    Serial.print("Touchpad: ");
    Serial.println(toggle[11]);
  }
  if(ps5.event.button_down.up) {
    toggle[12] = !toggle[12];
    Serial.print("Up: ");
    Serial.println(toggle[12]);
  }
  if(ps5.event.button_down.down) {
    toggle[13] = !toggle[13];
    Serial.print("Down: ");
    Serial.println(toggle[13]);
  }
  if(ps5.event.button_down.left) {
    toggle[14] = !toggle[14];
    Serial.print("Left: ");
    Serial.println(toggle[14]);
  }
}


#include <connectps5.h>
#include <Movement.h>
#include <ESP32Servo.h>

#define motorLF    32
#define motorLR   14
#define motorRF    25
#define motorRB   33
#define motorFF    27
#define motorFB   26

#define motor_axisX_L 22
#define motor_axisX_R 23

#define motor_axisY_L 18
#define motor_axisY_R 19

#define limitsw_R 5
#define limitsw_L 4

Servo servo;
int servoAngle = 0;
int stepAngle = 3;
unsigned long lastMove = 0;
int servoInterval = 15; 

// ===== Semi Auto สำหรับแกน Y =====

unsigned long semiStartTime = 0;
bool semiRunning = false;

// ปรับค่าได้
int semiForwardTime = 120;   // เวลาแทง (ms)
int semiBackwardTime = 120;  // เวลาดึงกลับ (ms)
int semiSpeed = 50;         // ความแรงของแกน Y


int pwm_normal = 50 ;
int pwm_auto = 100 ;

void setup() {
  Serial.begin(115200);
  ps5.attachOnConnect(onConnect);
  ps5.attachOnDisconnect(onDisConnect);
  ps5.attach(onEvent);
  ps5.begin("A0:FA:9C:AF:72:48"); // เปลี่ยนเป็น MAC ของ PS5 Controller
  Serial.println("Bluetooth Ready.");

  // Pinmode
  pinMode(motorLF, OUTPUT);
  pinMode(motorLR, OUTPUT); // Omi Left
  pinMode(motorRF, OUTPUT);
  pinMode(motorRB, OUTPUT); // Omi Right
  pinMode(motorFF, OUTPUT);
  pinMode(motorFB, OUTPUT); // Omi Front 
  pinMode(motor_axisX_L, OUTPUT);
  pinMode(motor_axisX_R, OUTPUT);
  pinMode(motor_axisY_L, OUTPUT);
  pinMode(motor_axisY_R, OUTPUT);
  pinMode(limitsw_R, INPUT_PULLUP);
  pinMode(limitsw_L, INPUT_PULLUP);
  servo.attach(21);
  servo.write(servoAngle);   // ไปที่มุม 0 ตอนเริ่มทำงาน

}

void loop() {
  int LX = ps5.LStickX(); // Analog Left
  int LY = ps5.LStickY();
  int RX = ps5.RStickX(); 
  int RY = ps5.RStickY(); 
  int Share = toggle[8]; //ปุ่มเปลี่ยนอนาล็อคซ้ายขวาขวาซ้าย
  int L2 = ps5.L2(); //ปุ่มลดความเร็ว(ปุ่มSlow)
  int Options = ps5.Options(); //ปุ่มResetมอเตอร์แกนX
  int L1 = ps5.L1(); //ปุ่มหมุนซ้ายแกนX
  int R1 = ps5.R1();//ปุ่มหมุนขวาแกนX
  int Triangle = ps5.Triangle(); //ปุ่มหมุนตามเข็มแกนY
  int Cross = ps5.Cross(); //int Cross = ps5.Cross();
  int Up = ps5.Up();//ปุ่มหมุนตามเข็มServo
  int Down = ps5.Down();// ปุ่มหมุนทวนเข็มServo
  int Square = ps5.Square(); //ปุ่มResetServo
  int R2 = ps5.R2(); // (SemiAuto) พุ่งแทง
  int Circle = ps5.Circle(); //(SemiAuto) พุ่งแทงลูกโป่งสูง
  int Right = ps5.Right();
  int Left = ps5.Left();

  logData("Speed", RY);
  logData("Strafe", RX);
  logData("Turn", LX);
  logData("AnalogMode", Share);
  logData("ArmX_Left", L1);
  logData("ArmX_Right", R1);
  logData("ArmX_Reset", Options);
  logData("ArmY_CW", Triangle);
  logData("ArmY_CCW", Cross);
  logData("Servo_CW", Up);
  logData("Servo_CCW", Down);
  logData("Attack_Low", R2);
  logData("Attack_High", Circle);
  logData("SlowMode", L2);
  logData("Stop", Square);
  Serial.println(); // ขึ้นบรรทัดใหม่

  if (Share == 1){
    drive_omni3(RY,RX,LX,L2);
  }else{
    drive_omni3(LY,LX,RX,L2);
  }
  ArmX(R1,L1,Options,pwm_normal); // แกนX
  ArmY(Triangle,Cross,pwm_normal); //แกนY
  servoY(Up,Down,Square,Right,Left);
  SemiAuto_Y(R2);

  delay(70);
}

void logData(String label, int value) {
  Serial.print("[");
  Serial.print(label);
  Serial.print(":");
  Serial.print(value);
  Serial.print("] ");
}


void drive_omni3(int speed, int strafe, int turn, int mode) {
  // จำกัดอินพุตจากจอยให้อยู่ในช่วง -128 ถึง 128
  speed  = constrain(speed, -128, 128);   // แกน Y (เดินหน้า–ถอยหลัง)
  strafe = constrain(strafe, -128, 128);  // แกน X (เลี้ยวซ้าย–ขวา/สไลด์ข้าง)
  turn   = constrain(turn, -128, 128);    // หมุนรอบตัว

  float x = strafe;   // ซ้าย/ขวา
  float y = speed;    // หน้า/หลัง
  float w = turn;     // หมุนรอบตัว


  float motorF = -w + x;                        // ล้อหน้า (motorFF/motorFB)
  float motorR = -w - 0.5f * x - 0.866f * y;    // ล้อขวา  (motorRF/motorRB)
  float motorL = -w - 0.5f * x + 0.866f * y;    // ล้อซ้าย (motorLF/motorLR)

  // === โหมด Slow===
  if (mode == 1) {   // ถ้า L2 กด = 1
    motorF /= 2.0f;
    motorR /= 2.0f;
    motorL /= 2.0f;
  }

  // === Normalize===
  float maxMotor = max(max(fabs(motorF), fabs(motorR)), fabs(motorL));
  if (maxMotor > 128.0f) {
    float scale = 128.0f / maxMotor;
    motorF *= scale;
    motorR *= scale;
    motorL *= scale;
  }

  motorF = adjust_speed(motorF);
  motorR = adjust_speed(motorR);
  motorL = adjust_speed(motorL);

  ControlMotor(motorL, motorLF, motorLR);   // ล้อซ้าย
  ControlMotor(motorR, motorRF, motorRB);   // ล้อขวา
  ControlMotor(motorF, motorFF, motorFB);   // ล้อหน้า
}

float adjust_speed(float speed) {
  if (abs(speed) < 10) return 0; 
  return speed;
}
void ControlMotor(float speed, int in1, int in2) {
  int pwm = map(abs(speed), 0, 128, 0, 255);

  if (speed > 0) {
    analogWrite(in1, pwm);
    analogWrite(in2, LOW);   
  } 
  else if (speed < 0) {

    analogWrite(in1, LOW);
    analogWrite(in2, pwm);
  } 
  else {
    analogWrite(in1, LOW);
    analogWrite(in2, LOW);
  }
}

void ArmX(int press_R,int press_L,int press_Reset,int pwm_normal){
  bool LeftLimit = digitalRead(limitsw_L);
  bool RightLimit = digitalRead(limitsw_R);

  if (press_Reset ==1){
    if(RightLimit == HIGH){
      analogWrite(motor_axisX_L,LOW);
      analogWrite(motor_axisX_R,100);
    }else if(RightLimit == LOW){
      analogWrite(motor_axisX_L,LOW);
      analogWrite(motor_axisX_R,LOW);
    }
    return;
  }
  if (press_R == 1 && RightLimit == LOW){
    analogWrite(motor_axisX_L,LOW);
    analogWrite(motor_axisX_R,LOW);
    //Serial.println("ชนขวา");
  }else if (press_L ==1 &&LeftLimit == HIGH){
    analogWrite(motor_axisX_R,LOW);
    analogWrite(motor_axisX_L,LOW);
    //Serial.println"ชนซ้าย");
  }else if (press_R == 1){
    analogWrite(motor_axisX_R,pwm_normal);
    analogWrite(motor_axisX_L,LOW);
    //Serial.println("เคลื่อนที่ขวา");
  }else if (press_L == 1){
    analogWrite(motor_axisX_R,LOW);
    analogWrite(motor_axisX_L,pwm_normal);
    //Serial.println("เคลื่อนที่ซ้าย");
  }else{
    analogWrite(motor_axisX_R,LOW);
    analogWrite(motor_axisX_L,LOW);
    //Serial.println("ไม่ทำอ่ะไร");
  }
}
void ArmY(int CW,int CCW,int pwm_normal){
  if (CW ==1){
    analogWrite(motor_axisY_R,pwm_normal);
    analogWrite(motor_axisY_L,LOW);
  }else if (CCW ==1){
    analogWrite(motor_axisY_R,LOW);
    analogWrite(motor_axisY_L,pwm_normal);
  }
  return;
}
void servoY(int CW, int CCW, int reset, int set90, int set180) {
  unsigned long now = millis();

  if (now - lastMove < servoInterval) return; 
  lastMove = now;

  // --- RESET มุมทันที = 0 ---
  if (reset == 1) {
    servoAngle = 0;
    servo.write(0);
    return;  
  }

  // --- ตั้งมุม 90 องศา ---
  if (set90 == 1) {
    servoAngle = 90;
    servo.write(90);
    return;
  }

  // --- ตั้งมุม 180 องศา ---
  if (set180 == 1) {
    servoAngle = 180;
    servo.write(180);
    return;
  }

  // --- หมุนตามเข็มแบบเดิม ---
  if (CW == 1) {
    servoAngle += stepAngle;
    if (servoAngle > 180) servoAngle = 180;
    servo.write(servoAngle);
    return;
  }

  // --- หมุนทวนเข็มแบบเดิม ---
  if (CCW == 1) {
    servoAngle -= stepAngle;
    if (servoAngle < 0) servoAngle = 0;
    servo.write(servoAngle);
    return;
  }
}

void SemiAuto_Y(int trigger) {

  // เริ่มทำงานครั้งแรก
  if (trigger == 1 && !semiRunning) {
    semiRunning = true;
    semiStartTime = millis();
  }

  if (semiRunning) {
    unsigned long t = millis() - semiStartTime;

    // ---- ช่วงแทง ----
    if (t < semiForwardTime) {
      analogWrite(motor_axisY_R, semiSpeed);
      analogWrite(motor_axisY_L, LOW);
    }

    // ---- ช่วงดึงกลับ ----
    else if (t < semiForwardTime + semiBackwardTime) {
      analogWrite(motor_axisY_R, LOW);
      analogWrite(motor_axisY_L, semiSpeed);
    }

    // ---- จบ ----
    else {
      analogWrite(motor_axisY_R, LOW);
      analogWrite(motor_axisY_L, LOW);
      semiRunning = false;
    }
  }
}