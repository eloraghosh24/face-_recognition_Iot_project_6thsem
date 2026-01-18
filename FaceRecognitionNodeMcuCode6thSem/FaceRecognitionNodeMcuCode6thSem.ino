#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

// WiFi credentials
const char* ssid = "✨ɪт'ѕ мє иιℓ✨";
const char* password = "53459313";

// Create web server
ESP8266WebServer server(80);

// Servo setup
Servo doorLock;
const int servoPin = D2;  // NodeMCU D2 pin for servo control
const int LED_PIN = D4;   // Built-in LED for status indication

void setup() {
  Serial.begin(115200);
  
  // Initialize servo
  doorLock.attach(servoPin);
  doorLock.write(0);  // Initial position (locked)
  
  // Setup LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);  // LED off initially
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  
  // Define API endpoints
  server.on("/open", HTTP_GET, handleDoorOpen);
  server.on("/close", HTTP_GET, handleDoorClose);
  server.on("/status", HTTP_GET, handleStatus);
  
  server.begin();
}

void loop() {
  server.handleClient();
}

// Handle door open request
void handleDoorOpen() {
  doorLock.write(90);  // Rotate servo to open position
  digitalWrite(LED_PIN, HIGH);  // LED on
  server.send(200, "application/json", "{\"status\":\"open\"}");
}


// Handle door close request
void handleDoorClose() {
  doorLock.write(0);  // Rotate servo to closed position
  digitalWrite(LED_PIN, LOW);  // LED off
  server.send(200, "application/json", "{\"status\":\"closed\"}");
}

// Handle status request
void handleStatus() {
  int position = doorLock.read();
  String status = (position > 45) ? "open" : "closed";
  server.send(200, "application/json", "{\"status\":\"" + status + "\"}");
}
