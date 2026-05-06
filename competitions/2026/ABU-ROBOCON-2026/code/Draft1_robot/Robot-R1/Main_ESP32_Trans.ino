#include <ps5Controller.h>

bool toggle[16] = {false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false};

unsigned long previousMillis = 0;
const long interval = 100;

int clutch_percent = ps5.L2() * 100 / 255;

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
  if(ps5.event.button_down.options) {
    toggle[15] = !toggle[15];
    Serial.print("Option: ");
    Serial.println(toggle[15]);
  }
}

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  ps5.attachOnConnect(onConnect);
  ps5.attachOnDisconnect(onDisConnect);
  ps5.attach(onEvent);
  ps5.begin("A0:FA:9C:AF:72:48"); // เปลี่ยนเป็น MAC ของ PS5 Controller
  Serial.println("Bluetooth Ready.");
}

void loop() {
  int leftX = ps5.LStickX();
  int leftY = ps5.LStickY();
  int rightX = ps5.RStickX();
  int rightY = ps5.RStickY();
  int gripper_waepon = toggle[2];
  int Square = ps5.Square();
  //ps5.Cross();
  int slow_mode = ps5.L2();
  int manual_rack_down = ps5.R2();
  int L1 = ps5.L1();
  int manual_rack_up = ps5.R1();
  int mode = toggle[15]; //Option
  int weapon_180 = ps5.Triangle();
  int weapon_gripingfromrack = ps5.Cross();
  // int Cross = ps5.Cross();
  // int Left = ps5.Left();
  // int Right = ps5.Right();
  // int Options = ps5.Options();
  int touchpad = toggle[11];
  //int Share = ps5.Share();
  if (weapon_180 ==1 && weapon_gripingfromrack ==1){
    weapon_180 = 0 ;
    weapon_gripingfromrack = 0;
  } 

String messageToSend = String(leftX) + "," + //String(rightY) TURN
                       String(leftY)+ "," + //speed
                       String(rightX) + "," + //stafe
                       String(gripper_waepon) + "," +  //Circle
                       String(slow_mode) + "," +  //L2
                       String(manual_rack_down) + "," + // R2
                       String(manual_rack_up) + "," + //R1  
                       String(weapon_180) + "," +//สามเหลี่ยม
                       String(weapon_gripingfromrack) + "," + "\n";

  Serial.print(messageToSend);
  Serial1.print(messageToSend);
  

  delay(60);

  // set mode color
  // if(touchpad == 0){
  //   ps5.setLed(0, 0, 255);
  //   ps5.sendToController();
  // }
  // else if(touchpad == 1){
  //   ps5.setLed(255, 0, 0);
  //   ps5.sendToController();
  // }
}