#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <TimeLib.h>

#define RST_PIN D0
#define SS_PIN D8
#define SERVO_PIN D2
#define GREEN_LED D3
#define RED_LED D4

// WiFi Configuration
const char* ssid = "✨ɪт'ѕ мє иιℓ✨";
const char* password = "53459313";

// Telegram Configuration
const String botToken = "8170191722:AAFCcjWwD_DxO6jfuHl8q0aucFO2yWKUJRw";
const String chatID = "1231793770";
const String telegramURL = "https://api.telegram.org/bot" + botToken + "/sendMessage";

// NTP Configuration for IST (UTC+5:30)
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 19800, 60000); // 19800 seconds = 5h 30m

MFRC522 mfrc522(SS_PIN, RST_PIN);
Servo myServo;

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

  // Hardware Setup
  myServo.attach(SERVO_PIN);
  myServo.write(0);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnected to WiFi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    
    // Initialize NTP client
    timeClient.begin();
    timeClient.update();
  } else {
    Serial.println("\nFailed to connect to WiFi!");
  }
}

void loop() {
  timeClient.update(); // Update time regularly
  
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String identifier = checkAuthorization();
    
    if (identifier != "") {
      grantAccess(identifier);
      sendTelegramAlert(identifier, true);
    } else {
      String unknownUID = getUIDString();
      denyAccess(unknownUID);
      sendTelegramAlert(unknownUID, false);
    }
    
    mfrc522.PICC_HaltA();
    delay(1000);
  }
}

void sendTelegramAlert(String identifier, bool isAuthorized) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Telegram Alert Failed: No WiFi connection");
    return;
  }

  WiFiClientSecure client;
  HTTPClient https;
  client.setInsecure();
  
  String message = isAuthorized ? 
    ("🚨 Authorized Access\n👤 User: " + identifier + "\n⏰ Time: " + getFormattedTime() + "\n📍 Door Unlocked Successfully!") :
    ("🚫 Unauthorized Access\n🔑 Unknown UID: " + identifier + "\n⏰ Time: " + getFormattedTime() + "\n📍 Door Opening Revoked!");

  String url = telegramURL;
  String payload = "chat_id=" + chatID + "&text=" + urlEncode(message);

  if (https.begin(client, url)) {
    https.addHeader("Content-Type", "application/x-www-form-urlencoded");
    
    int httpCode = https.POST(payload);
    
    if (httpCode == HTTP_CODE_OK) {
      String response = https.getString();
      Serial.println("Telegram Response: " + response);
    } else {
      Serial.print("Telegram Error Code: ");
      Serial.println(httpCode);
      Serial.print("Error Response: ");
      Serial.println(https.getString());
    }
    
    https.end();
  } else {
    Serial.println("Failed to connect to Telegram API");
  }
}

String getUIDString() {
  String uidStr = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uidStr += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uidStr += String(mfrc522.uid.uidByte[i], HEX);
    if (i < mfrc522.uid.size - 1) uidStr += ":";
  }
  uidStr.toUpperCase();
  return uidStr;
}

String getFormattedTime() {
  timeClient.update();
  time_t epochTime = timeClient.getEpochTime();
  
  // Convert epoch time to local time components
  // Use different variable names to avoid conflict with TimeLib functions
  int currentHour = hour(epochTime);
  int currentMinute = minute(epochTime);
  int currentSecond = second(epochTime);
  int currentDay = day(epochTime);
  int currentMonth = month(epochTime);
  int currentYear = year(epochTime);

  // Format time string
  char timeString[25];
  sprintf(timeString, "%02d:%02d:%02d | %02d/%02d/%04d", 
          currentHour, currentMinute, currentSecond, 
          currentDay, currentMonth, currentYear);
          
  return String(timeString);
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
  digitalWrite(GREEN_LED, HIGH);
  myServo.write(90);
  delay(5000);
  myServo.write(0);
  digitalWrite(GREEN_LED, LOW);
}

void denyAccess(String uid) {
  Serial.print("Access Denied! UID: ");
  Serial.println(uid);
  digitalWrite(RED_LED, HIGH);
  delay(1000);
  digitalWrite(RED_LED, LOW);
}

String urlEncode(String str) {
  String encodedString = "";
  char c;
  for (unsigned int i = 0; i < str.length(); i++) {
    c = str.charAt(i);
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
      encodedString += c;
    } else if (c == ' ') {
      encodedString += "%20";
    } else if (c == '\n') {
      encodedString += "%0A";
    } else {
      char buf[4];
      sprintf(buf, "%%%02X", c);
      encodedString += buf;
    }
  }
  return encodedString;
}
