int slow_mode = 0,mode =0;
int rack_down_AxisY =0, rack_up_AxisY = 0;
int speed = 0, strafe = 0, turn = 0,gripper_waepon =0;
int weapon_180 = 0, weapon_gripingfromrack = 0;

int motor_PWM = 70;

///////////ENCODER////////////
const int encoderA = 20;
const int encoderB = 21;

const int PWMpin = 10;
const int IN1 = 9;
const int IN2 = 8;

volatile long encoderCount = 0;

int speedPWM = 150;
int brakeOffset = 10;
///////////ENCODER////////////


// มอเตอร์ล้อ4 ล้อ
#define motorLF1    32
#define motorLFPMW   2
#define motorLB1    33
#define motorLBPMW   3
#define motorRF1    34
#define motorRFPMW   4
#define motorRB1    35
#define motorRBPMW   13

#define manual_rack_down  26
#define manual_rack_up  27
#define motorPWM     6

#define gripper 16

#define limitDown   30
#define limitup     31


void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);

  pinMode(motorLF1, OUTPUT);
  pinMode(motorLFPMW, OUTPUT);
  pinMode(motorLB1, OUTPUT);
  pinMode(motorLBPMW, OUTPUT);
  pinMode(motorRF1, OUTPUT);
  pinMode(motorRFPMW, OUTPUT);
  pinMode(motorRB1, OUTPUT);
  pinMode(motorRBPMW, OUTPUT);

  pinMode(limitup, INPUT_PULLUP);
  pinMode(limitDown, INPUT_PULLUP);
  
  pinMode(encoderA, INPUT_PULLUP);
  pinMode(encoderB, INPUT_PULLUP);

  pinMode(PWMpin, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  // attachInterrupt(digitalPinToInterrupt(encoderA), readEncoder, CHANGE);

  Serial.print("P PHET");
}

void loop() {
 
  readAndParseSerial1();
  drive_manual(turn, speed, strafe, mode);
  move_rack(rack_down_AxisY, rack_up_AxisY);
  Grip(gripper_waepon);
  // control_encoder(weapon_180,weapon_gripingfromrack);
  motorgripper(weapon_180,weapon_gripingfromrack);

  delay(60);
}

void readAndParseSerial1() {
  static String inputData = "";

  while (Serial1.available()) {
    char c = Serial1.read();
    if (c == '\n') {
      int values[25];
      int index = 0;
      int lastIndex = 0;

      for (int i = 0; i < inputData.length(); i++) {
        if (inputData.charAt(i) == ',') {
          values[index++] = inputData.substring(lastIndex, i).toInt();
          lastIndex = i + 1;
        }
      }
      values[index] = inputData.substring(lastIndex).toInt();

      if (index >= 8) {
        turn   = values[0];
        speed  = values[1];
        strafe = values[2];
        gripper_waepon = values[3];
        slow_mode = values[4];
        rack_down_AxisY = values[5];
        rack_up_AxisY = values[6];
        weapon_180 = values[7];
        weapon_gripingfromrack = values[8];
      }

      Serial.print("RECEIVED: ");
      Serial.println(inputData);

      inputData = "";
    } else {
      inputData += c;
    }
  }
}

void drive_manual(int speed, int strafe, int turn, int mode) {
  if (mode == 1) {
    speed = -speed;
    strafe = -strafe;
  }

  int motor1Speed, motor2Speed, motor3Speed, motor4Speed;

  if (slow_mode == 1) {
    motor1Speed = (speed + strafe + turn) / 4;
    motor2Speed = (speed - strafe - turn) / 4;
    motor3Speed = (speed - strafe + turn) / 4;
    motor4Speed = (speed + strafe - turn) / 4;
  } else {
    motor1Speed = (speed + strafe + turn) / 2;
    motor2Speed = (speed - strafe - turn) / 2;
    motor3Speed = (speed - strafe + turn) / 2;
    motor4Speed = (speed + strafe - turn) / 2;
  }

  motor1Speed = adjust_speed(motor1Speed);
  motor2Speed = adjust_speed(motor2Speed);
  motor3Speed = adjust_speed(motor3Speed);
  motor4Speed = adjust_speed(motor4Speed);

  int maxMotorSpeed = max(max(abs(motor1Speed), abs(motor2Speed)), max(abs(motor3Speed), abs(motor4Speed)));
  if (maxMotorSpeed > 128) {
    motor1Speed = (motor1Speed * 128) / maxMotorSpeed;
    motor2Speed = (motor2Speed * 128) / maxMotorSpeed;
    motor3Speed = (motor3Speed * 128) / maxMotorSpeed;
    motor4Speed = (motor4Speed * 128) / maxMotorSpeed;
  }

  ControlMotor(motor1Speed, motorLF1, motorLFPMW);
  ControlMotor(motor2Speed, motorRF1, motorRFPMW);
  ControlMotor(motor3Speed, motorLB1, motorLBPMW);
  ControlMotor(motor4Speed, motorRB1, motorRBPMW);
}

void ControlMotor(int speed, int A, int PWM) {
  digitalWrite(A, (speed > 0) ? HIGH : LOW);
  int pwmVal = map(abs(speed), 0, 128, 0, 255);
  analogWrite(PWM, constrain(pwmVal, 0, 255));
}

int adjust_speed(int speed) {
  return (abs(speed) < 10) ? 0 : speed;
}

void move_rack(int md, int mu) {
  bool downState = digitalRead(limitDown);
  bool upState = digitalRead(limitup);

  // if (mu == 1 && upState == LOW) {
  //   analogWrite(motorPWM, 0);
  //   digitalWrite(manual_rack_down, HIGH);
  //   digitalWrite(manual_rack_up, HIGH);
  // } else if (md == 1 && downState == LOW) {
  //   analogWrite(motorPWM, 0);
  //   digitalWrite(manual_rack_down, HIGH);
  //   digitalWrite(manual_rack_up, HIGH);
  // } else if (mu == 1) {
  //   analogWrite(motorPWM, 150);
  //   digitalWrite(manual_rack_down, LOW);
  //   digitalWrite(manual_rack_up, HIGH);
  // } else if (md == 1) {
  //   analogWrite(motorPWM, 20);
  //   digitalWrite(manual_rack_down, HIGH);
  //   digitalWrite(manual_rack_up, LOW);
  // } else {
  //   analogWrite(motorPWM, 0);
  //   digitalWrite(manual_rack_down, HIGH);
  //   digitalWrite(manual_rack_up, HIGH);
  // }
    if (md ==1 && mu == 0){
      analogWrite(motorPWM, 20);
      digitalWrite(manual_rack_down, LOW);
      digitalWrite(manual_rack_up, HIGH);
      // Serial.print("1");
    } else if (mu ==1 && md ==0){
      analogWrite(motorPWM, 100);
      digitalWrite(manual_rack_down, HIGH);
      digitalWrite(manual_rack_up, LOW);
      // Serial.print("2");
    } else{
      analogWrite(motorPWM, 0);
      digitalWrite(manual_rack_down, LOW);
      digitalWrite(manual_rack_up, LOW);
      // Serial.print("3");
    }
}

void Grip(int GW){
  if (GW == 1){
    digitalWrite(gripper, HIGH);
    //Serial.print("1");
  }else{
    digitalWrite(gripper, LOW);
    //Serial.print("2");
  }
  
}

// void control_encoder(int w180,int wg) {
//   if (w180 == -1){
//     moveTo(180, 1);
//     Serial.print("1");
//   }
//   if (wg == 1){
//     moveTo(180, -1);
//     Serial.print("2");
//   }
// }

// แก้ตรงนี้เท่านั้น
// void moveTo(int targetPulse, int direction) {

//   encoderCount = 0;
//   unsigned long startTime = millis();

//   while (1) {

//     // timeout ลดเหลือ 200ms (ลื่นขึ้นมาก)
//     if (millis() - startTime > 200) {
//       Serial.println("TIMEOUT");
//       break;
//     }

//     if (abs(encoderCount) < targetPulse - brakeOffset) {

//       if (direction == 1) {
//         digitalWrite(IN1, HIGH);
//         digitalWrite(IN2, LOW);
//       } else {
//         digitalWrite(IN1, LOW);
//         digitalWrite(IN2, HIGH);
//       }

//       analogWrite(PWMpin, speedPWM);
//     }
//     else {
//       break;
//     }

//     delay(1);   // สำคัญมาก ลดอาการค้าง
//   }

//   //  stop motor (ออกจาก loop แล้วค่อยหยุด)
//   analogWrite(PWMpin, 0);
//   digitalWrite(IN1, HIGH);
//   digitalWrite(IN2, HIGH);
// }

// void readEncoder() {
//   if (digitalRead(encoderB) == HIGH) {
//     encoderCount++;
//   } else {
//     encoderCount--;
//   }
// }

////////////เบื้องต้นของEncoder////////////
void motorgripper(int w180,int wg){
  if (w180 == 1 && wg ==0){
    analogWrite(PWMpin, 80);
    digitalWrite(IN1,HIGH);
    digitalWrite(IN2,LOW);
  } else if (w180 ==0 && wg ==1){
    analogWrite(PWMpin, 50);
    digitalWrite(IN1,LOW);
    digitalWrite(IN2,HIGH);
  }else{
    analogWrite(PWMpin, HIGH);
    digitalWrite(IN1,LOW);
    digitalWrite(IN2,LOW);
  }
}
////////////เบื้องต้นของEncoder////////////