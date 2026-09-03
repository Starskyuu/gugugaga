/*
 * ESP32 differential-thrust motor bridge.
 * Input over USB serial at 115200 baud: {"left":0.25,"right":-0.10}\n
 * Requires ArduinoJson 7.  Adjust pins to match the motor driver board.
 */
#include <ArduinoJson.h>

const int LEFT_PWM = 25;
const int LEFT_DIR = 26;
const int RIGHT_PWM = 27;
const int RIGHT_DIR = 14;
const int ENABLE_PIN = 33;
const unsigned long COMMAND_TIMEOUT_MS = 500;
unsigned long lastCommandMs = 0;

void setOneMotor(int pwmPin, int dirPin, float value) {
  value = constrain(value, -1.0f, 1.0f);
  digitalWrite(dirPin, value >= 0 ? HIGH : LOW);
  analogWrite(pwmPin, (int)(fabs(value) * 255.0f));
}

void stopMotors() {
  analogWrite(LEFT_PWM, 0);
  analogWrite(RIGHT_PWM, 0);
  digitalWrite(ENABLE_PIN, LOW);
}

void setup() {
  pinMode(LEFT_PWM, OUTPUT);
  pinMode(LEFT_DIR, OUTPUT);
  pinMode(RIGHT_PWM, OUTPUT);
  pinMode(RIGHT_DIR, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  stopMotors();
  Serial.begin(115200);
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, line);
    if (!error && doc["left"].is<float>() && doc["right"].is<float>()) {
      digitalWrite(ENABLE_PIN, HIGH);
      setOneMotor(LEFT_PWM, LEFT_DIR, doc["left"].as<float>());
      setOneMotor(RIGHT_PWM, RIGHT_DIR, doc["right"].as<float>());
      lastCommandMs = millis();
      Serial.println("{\"ok\":true}");
    } else {
      stopMotors();
      Serial.println("{\"ok\":false,\"reason\":\"bad_json\"}");
    }
  }
  if (millis() - lastCommandMs > COMMAND_TIMEOUT_MS) {
    stopMotors();
  }
}

