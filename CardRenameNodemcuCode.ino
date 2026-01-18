#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN D0
#define SS_PIN D8
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Custom card database
struct Card {
  byte uid[4];
  String name;
};

// Updated with your cards
Card authorizedCards[] = {
  {{0xD1, 0x5E, 0xE6, 0x19}, "Nilimesh29"},  // First card
  {{0x63, 0x5E, 0x08, 0x31}, "Soumak53"}      // Second card
};

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("RFID System Ready");
}

void loop() {
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String cardName = checkCard();
    
    if (cardName != "") {
      Serial.print("Authorized User: ");
      Serial.println(cardName);
    } else {
      Serial.print("Unknown Card UID: ");
      printUID();
    }
    
    mfrc522.PICC_HaltA();
    delay(500);
  }
}

String checkCard() {
  for (int i = 0; i < sizeof(authorizedCards)/sizeof(Card); i++) {
    if (memcmp(mfrc522.uid.uidByte, authorizedCards[i].uid, 4) == 0) {
      return authorizedCards[i].name;
    }
  }
  return "";
}

void printUID() {
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " ");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
  }
  Serial.println();
}