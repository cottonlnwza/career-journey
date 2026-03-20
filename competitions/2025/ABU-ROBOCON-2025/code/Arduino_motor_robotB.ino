#include <Servo.h>

// ตัวแปรจาก Serial1
int speed = 0, strafe = 0, turn = 0;
int auto_up = 0, Spread = 0;
int rackup = 0, slow_mode = 0;
int manual_rack_down = 0, manual_rack_up = 0;
int pinA = 0, pinB = 0, feed = 0, shoot = 0, openroller = 0, mode = 0;

// มอเตอร์
#define motorLF1    32
#define motorLFPMW   2
#define motorLB1    33
#define motorLBPMW   3
#define motorRF1    34
#define motorRFPMW   4
#define motorRB1    35
#define motorRBPMW   5

#define motorRACK1  26
#define motorRACK2  27
#define motorPWM     6
#define feed_ball   36

// ลิมิตสวิตช์
#define limitDown   30
#define limitup     31

// Servo
Servo rol1;
Servo rol2;

void setup() {
  Serial.begin(115200);

  pinMode(motorLF1, OUTPUT);
  pinMode(motorLFPMW, OUTPUT);
  pinMode(motorLB1, OUTPUT);
  pinMode(motorLBPMW, OUTPUT);
  pinMode(motorRF1, OUTPUT);
  pinMode(motorRFPMW, OUTPUT);
  pinMode(motorRB1, OUTPUT);
  pinMode(motorRBPMW, OUTPUT);
  pinMode(motorRACK1, OUTPUT);
  pinMode(motorRACK2, OUTPUT);
  pinMode(motorPWM, OUTPUT);
  pinMode(feed_ball, OUTPUT);

  pinMode(limitup, INPUT_PULLUP);
  pinMode(limitDown, INPUT_PULLUP);

  rol1.attach(7);
  rol2.attach(8);

  Serial.println("Setup Ready");
}

void loop() {
  readAndParseSerial1();
  drive_manual(speed, strafe, turn, mode);
  move_rack(manual_rack_down, manual_rack_up);
  pass_ball(shoot);
  start_roller(openroller);
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

      if (index >= 10) {
        turn   = values[0];
        speed  = values[1];
        strafe = values[2];
        auto_up = values[3];
        slow_mode = values[4];
        manual_rack_up = values[5];
        manual_rack_down = values[6];
        openroller = values[7];
        shoot = values[8];
        mode = values[9];
        feed = values[10];
      }

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
    motor1Speed = (speed + strafe + turn) / 3;
    motor2Speed = (speed - strafe - turn) / 3;
    motor3Speed = (speed - strafe + turn) / 3;
    motor4Speed = (speed + strafe - turn) / 3;
  } else {
    motor1Speed = (speed + strafe + turn);
    motor2Speed = (speed - strafe - turn);
    motor3Speed = (speed - strafe + turn);
    motor4Speed = (speed + strafe - turn);
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

  if (mu == 1 && upState == LOW) {
    analogWrite(motorPWM, 0);
    digitalWrite(motorRACK1, HIGH);
    digitalWrite(motorRACK2, HIGH);
  } else if (md == 1 && downState == LOW) {
    analogWrite(motorPWM, 0);
    digitalWrite(motorRACK1, HIGH);
    digitalWrite(motorRACK2, HIGH);
  } else if (mu == 1) {
    analogWrite(motorPWM, 150);
    digitalWrite(motorRACK1, LOW);
    digitalWrite(motorRACK2, HIGH);
  } else if (md == 1) {
    analogWrite(motorPWM, 20);
    digitalWrite(motorRACK1, HIGH);
    digitalWrite(motorRACK2, LOW);
  } else {
    analogWrite(motorPWM, 0);
    digitalWrite(motorRACK1, HIGH);
    digitalWrite(motorRACK2, HIGH);
  }
}
// test comment

void pass_ball(int pb) {
  digitalWrite(feed_ball, (pb == 1) ? HIGH : LOW);
}

void start_roller(int rp) {
  if (rp == 1) {
    rol1.writeMicroseconds(1250);
    rol2.writeMicroseconds(1250);
  } else {
    rol1.writeMicroseconds(0);
    rol2.writeMicroseconds(0);
  }
}