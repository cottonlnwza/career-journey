// --- Motor Pins (Left Front) ---
#define LEFT_FRONT_IN1 26
#define LEFT_FRONT_IN2 27
#define LEFT_FRONT_PWM 4

// --- Motor Pins (Left Back) ---
#define LEFT_BACK_IN1 28
#define LEFT_BACK_IN2 29
#define LEFT_BACK_PWM 5

// --- Motor Pins (Right Front) ---
#define RIGHT_FRONT_IN1 30
#define RIGHT_FRONT_IN2 31
#define RIGHT_FRONT_PWM 6

// --- Motor Pins (Right Back) ---
#define RIGHT_BACK_IN1 32
#define RIGHT_BACK_IN2 33
#define RIGHT_BACK_PWM 7

// --- Relay Pins ---
#define RELAY1 8
#define RELAY2 9
#define RELAY3 10 //lift
#define RELAY4 11 //gripper
#define RELAY5 12 //angle

int speed = 0, strafe = 0, turn = 0, grap_spearhead = 0, assemble_spearhead = 0, release_spearhead = 0, grab_kungfu_scroll = 0, lift_kungfu_scroll = 0;
int state = 1;
void setup() {
  Serial.begin(115200);

  // Motor pins
  pinMode(LEFT_FRONT_IN1, OUTPUT);  pinMode(LEFT_FRONT_IN2, OUTPUT);  pinMode(LEFT_FRONT_PWM, OUTPUT);
  pinMode(LEFT_BACK_IN1, OUTPUT);   pinMode(LEFT_BACK_IN2, OUTPUT);   pinMode(LEFT_BACK_PWM, OUTPUT);
  pinMode(RIGHT_FRONT_IN1, OUTPUT); pinMode(RIGHT_FRONT_IN2, OUTPUT); pinMode(RIGHT_FRONT_PWM, OUTPUT);
  pinMode(RIGHT_BACK_IN1, OUTPUT);  pinMode(RIGHT_BACK_IN2, OUTPUT);  pinMode(RIGHT_BACK_PWM, OUTPUT);

  // Relay pins (default OFF)
  pinMode(RELAY1, OUTPUT); pinMode(RELAY2, OUTPUT);
  pinMode(RELAY3, OUTPUT); pinMode(RELAY4, OUTPUT);
  pinMode(RELAY5, OUTPUT);
  digitalWrite(RELAY1, LOW); digitalWrite(RELAY2, LOW);
  digitalWrite(RELAY3, LOW); digitalWrite(RELAY4, LOW);
  digitalWrite(RELAY5, LOW);

}

void loop() {
  /*if (Serial.available() > 0) {
    Serial.println("ready");
    // 2. อ่านข้อความทั้งหมดจนกว่าจะเจอตัวอักษรขึ้นบรรทัดใหม่ (\n)
    String receivedData = Serial.readStringUntil('\n');

    // 3. ตรวจสอบว่าข้อความไม่ว่างเปล่า
    if (receivedData.length() > 0) {
      
      // 4. ใช้ sscanf แยกข้อความที่มีรูปแบบ "x,y,z" ออกเป็นตัวเลข 3 ตัว
      // %d หมายถึงให้แปลงข้อมูลเป็นเลขจำนวนเต็ม (Integer)
      int parsed_items = sscanf(receivedData.c_str(), "%d,%d,%d", &speed, &strafe, &turn, &grap_spearhead, &assemble_spearhead, &release_spearhead, &grab_kungfu_scroll, &lift_kungfu_scroll);

      drive_robot(speed, strafe, turn);
    }
  }*/
  if(state == 1){
    drive_robot(30, 0, 0);
    delay(4400);
    drive_robot(0, 0, 0);
    delay(100);
    digitalWrite(RELAY4, HIGH);
    delay(300);
    digitalWrite(RELAY3, HIGH);
    delay(1000);
    drive_robot(-100, 0, 0);
    delay(1000);
    drive_robot(0, 0, 0);
    digitalWrite(RELAY3, LOW);
    delay(1000);
    digitalWrite(RELAY5, HIGH);
    delay(200);
    drive_robot(0, 0, 80);
    delay(2000);
    drive_robot(0, 0, 0);
    delay(15000);
    digitalWrite(RELAY4, LOW);

    state = 2;
    }
  else{
    drive_robot(0, 0, 0);
  }
 
}
