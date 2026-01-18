#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>

#define RST_PIN D0
#define SS_PIN D8
#define SERVO_PIN D2
#define GREEN_LED D3
#define RED_LED D4

MFRC522 mfrc522(SS_PIN, RST_PIN);
Servo myServo;

// Card database with names
struct Card {
  byte uid[4];
  String name;
};

Card authorizedCards[] = {
  {{0xD1, 0x5E, 0xE6, 0x19}, "Nilimesh29"},
  {{0x63, 0x5E, 0x04, 0x31}, "Bappa22"}
};

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();
  
  // Servo setup
  myServo.attach(SERVO_PIN);
  myServo.write(0); // Start in closed position
  
  // LED setup
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
  
  Serial.println("System Ready - Scan Your Card");
}

void loop() {
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String userName = checkAuthorization();
    
    if (userName != "") {
      grantAccess(userName);
    } else {
      denyAccess();
    }
    
    mfrc522.PICC_HaltA();
    delay(500); // Debounce delay
  }
}

String checkAuthorization() {
  for (int i = 0; i < sizeof(authorizedCards)/sizeof(Card); i++) {
    if (memcmp(mfrc522.uid.uidByte, authorizedCards[i].uid, 4) == 0) {
      return authorizedCards[i].name;
    }
  }
  return "";
}

void grantAccess(String user) {
  Serial.print("Access Granted to: ");
  Serial.println(user);
  
  // Open door with green LED
  digitalWrite(GREEN_LED, HIGH);
  myServo.write(90); // Open position
  delay(5000); // Keep open for 5 seconds
  
  // Close door and turn off LED
  myServo.write(0); 
  digitalWrite(GREEN_LED, LOW);
}

void denyAccess() {
  Serial.println("Access Denied!");
  
  // Red LED blink
  digitalWrite(RED_LED, HIGH);
  delay(1000);
  digitalWrite(RED_LED, LOW);
}
