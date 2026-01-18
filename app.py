from flask import Flask, render_template, jsonify, Response, request
from face_recognition import FaceLock
import threading
import os
import cv2
import logging
import requests
import time
from datetime import datetime

# Add logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ensure templates directory exists
if not os.path.exists('templates'):
    os.makedirs('templates')

# Create index.html if it doesn't exist
template_path = os.path.join('templates', 'index.html')
if not os.path.exists(template_path):
    with open(template_path, 'w') as f:
        f.write('''<!DOCTYPE html>
<html>
<!-- Copy the entire content of the index.html template here -->
</html>''')

face_lock = FaceLock()


class DoorController:
    def __init__(self):
        self.status = "closed"
        self.nodemcu_url = "http://192.168.0.105"  # Verified NodeMCU IP
        self.timeout = 5
        self.retry_attempts = 5
        self.retry_delay = 1.0
        self.last_command_time = 0
        self.min_command_interval = 2.0
        self.servo_movement_time = 1.5
        self.auto_close_delay = 10.0  # 10 seconds before auto-closing
        self.door_timer = None
        
    def verify_status(self):
        """Verify door status with NodeMCU"""
        try:
            response = requests.get(
                f"{self.nodemcu_url}/status",
                timeout=self.timeout,
                verify=False
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.status = data.get('status', self.status)
                    logger.debug(f"Door status verified: {self.status}")
                    return True
                except ValueError:
                    logger.error("Invalid JSON from NodeMCU status endpoint")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Status verification failed: {str(e)}")
            return False

    def check_connection(self):
        """Check NodeMCU connectivity with detailed logging"""
        try:
            logger.debug(f"Checking connection to NodeMCU at {self.nodemcu_url}")
            response = requests.get(
                f"{self.nodemcu_url}/status",
                timeout=self.timeout,
                verify=False
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.status = data.get('status', self.status)
                    logger.info(f"NodeMCU connected, status: {self.status}")
                    return True
                except ValueError:
                    logger.error("Invalid JSON response from NodeMCU")
                    return False
            else:
                logger.error(f"NodeMCU returned status code: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to NodeMCU at {self.nodemcu_url}")
            return False
        except requests.exceptions.Timeout:
            logger.error("Connection timeout")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def open_door(self):
        """Open door with verification and retry logic"""
        try:
            # Prevent rapid consecutive commands
            current_time = time.time()
            if current_time - self.last_command_time < self.min_command_interval:
                wait_time = self.min_command_interval - (current_time - self.last_command_time)
                logger.info(f"Waiting {wait_time:.1f}s before next command")
                time.sleep(wait_time)

            # Verify connection first
            if not self.check_connection():
                logger.error("Cannot open door - NodeMCU not responding")
                return False

            # Send open command with retries
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Sending open command (attempt {attempt + 1})")
                    response = requests.get(
                        f"{self.nodemcu_url}/open",
                        timeout=self.timeout,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        # Wait for servo movement
                        time.sleep(self.servo_movement_time)
                        
                        # Verify door opened successfully
                        if self.verify_status() and self.status == "open":
                            self.last_command_time = time.time()
                            logger.info("Door opened and verified")
                            self.schedule_auto_close()
                            return True
                            
                    logger.error(f"Open command failed (HTTP {response.status_code})")
                    time.sleep(self.retry_delay)
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Open attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(self.retry_delay)
                    
            return False
            
        except Exception as e:
            logger.error(f"Door control error: {str(e)}", exc_info=True)
            return False

    def close_door(self):
        """Close door with verification and retry logic"""
        try:
            # Prevent rapid consecutive commands
            current_time = time.time()
            if current_time - self.last_command_time < self.min_command_interval:
                wait_time = self.min_command_interval - (current_time - self.last_command_time)
                logger.info(f"Waiting {wait_time:.1f}s before closing")
                time.sleep(wait_time)

            # Verify connection first
            if not self.check_connection():
                logger.error("Cannot close door - NodeMCU not responding")
                return False

            # Send close command with retries
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Sending close command (attempt {attempt + 1})")
                    response = requests.get(
                        f"{self.nodemcu_url}/close",
                        timeout=self.timeout,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        # Wait for servo movement
                        time.sleep(self.servo_movement_time)
                        
                        # Verify door closed successfully
                        if self.verify_status() and self.status == "closed":
                            self.last_command_time = time.time()
                            logger.info("Door closed and verified")
                            return True
                            
                    logger.error(f"Close command failed (HTTP {response.status_code})")
                    time.sleep(self.retry_delay)
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Close attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(self.retry_delay)
                    
            return False
            
        except Exception as e:
            logger.error(f"Door control error: {str(e)}", exc_info=True)
            return False

    def schedule_auto_close(self):
        """Schedule automatic door closing"""
        def auto_close():
            logger.info("Auto-close timer triggered")
            self.close_door()
            self.door_timer = None

        # Cancel any existing timer
        if self.door_timer:
            self.door_timer.cancel()

        # Set new timer
        self.door_timer = threading.Timer(self.auto_close_delay, auto_close)
        self.door_timer.start()
        logger.info(f"Door will auto-close in {self.auto_close_delay} seconds")

# Initialize door controller
door_controller = DoorController()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_recognition():
    if not face_lock.running:
        def run_face_lock():
            face_lock.run()
        
        thread = threading.Thread(target=run_face_lock)
        thread.start()
        return jsonify({"status": "started", "message": "Face recognition started"})
    return jsonify({"status": "already_running", "message": "Face recognition already running"})

@app.route('/stop', methods=['POST'])
def stop():
    if face_lock.running:
        face_lock.stop()
        return jsonify({"status": "stopped", "message": "Face recognition stopped"})
    return jsonify({"status": "already_stopped", "message": "Face recognition not running"})

@app.route('/face_recognized', methods=['POST'])
def face_recognized():
    """Handle face recognition events"""
    try:
        data = request.json
        name = data.get('name')
        confidence = data.get('confidence', 0.0)
        is_unknown = data.get('is_unknown', False)

        if not face_lock.running:
            return jsonify({
                "status": "error",
                "message": "Face recognition not running"
            }), 400

        # Handle unknown faces
        if is_unknown or name == "Unknown":
            logger.info("Unknown face detected - ensuring door is closed")
            if door_controller.status == "open":
                door_controller.close_door()
            return jsonify({
                "status": "warning",
                "message": "Unknown face detected - door remains closed",
                "door_status": door_controller.status
            })

        # Log recognition details
        logger.info(f"Face recognition event: {name} ({confidence:.2%})")

        # Only proceed if confidence is high enough
        if confidence < 0.8:  # 80% threshold
            return jsonify({
                "status": "error",
                "message": "Confidence too low",
                "confidence": confidence
            }), 400

        # Verify NodeMCU connection
        if not door_controller.check_connection():
            error_msg = "\n".join([
                "NodeMCU not connected. Please check:",
                "1. NodeMCU power and WiFi connection",
                "2. Network connectivity (both devices on same subnet)",
                f"3. NodeMCU IP address (currently set to: {door_controller.nodemcu_url})",
                "4. No firewall blocking connections"
            ])
            logger.error(error_msg)
            return jsonify({
                "status": "error",
                "message": error_msg,
                "last_status": door_controller.status
            }), 503

        # Attempt door control
        logger.info(f"Opening door for {name}")
        success = door_controller.open_door()

        if success:
            # Schedule auto-close
            door_controller.schedule_auto_close()
            
            return jsonify({
                "status": "success",
                "message": f"Door opened for {name}",
                "door_status": door_controller.status,
                "confidence": confidence,
                "auto_close_in": door_controller.auto_close_delay,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({
            "status": "error",
            "message": "Failed to control door - Check hardware and network",
            "door_status": door_controller.status
        }), 500

    except Exception as e:
        logger.error(f"Face recognition handler error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def gen_frames():
    while True:
        if face_lock.running:
            try:
                frame = face_lock.current_frame
                if frame is not None:
                    # Add door status overlay
                    status_text = f"Door: {door_controller.status}"
                    cv2.putText(frame, status_text, (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Add auto-close timer if door is open
                    if door_controller.status == "open" and door_controller.door_timer:
                        time_left = max(0, door_controller.auto_close_delay - 
                                     (time.time() - door_controller.last_command_time))
                        timer_text = f"Auto-close in: {time_left:.1f}s"
                        cv2.putText(frame, timer_text, (10, 70), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        frame = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                logger.error(f"Frame generation error: {str(e)}")
                time.sleep(0.1)
        else:
            time.sleep(0.1)

@app.route('/door_status')
def get_door_status():
    """Get current door status"""
    try:
        # Verify NodeMCU connection
        connection_status = door_controller.check_connection()
        
        return jsonify({
            "status": door_controller.status,
            "connected": connection_status,
            "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Door status error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/network_test')
def network_test():
    """Test network connectivity to NodeMCU"""
    try:
        # Test basic ping
        try:
            import subprocess
            ping_result = subprocess.run(
                ['ping', '-n', '1', door_controller.nodemcu_url.replace('http://', '')],
                capture_output=True,
                text=True
            )
            ping_success = ping_result.returncode == 0
        except Exception as e:
            ping_success = False
            logger.error(f"Ping test failed: {str(e)}")

        # Test HTTP connection
        try:
            response = requests.get(
                f"{door_controller.nodemcu_url}/status",
                timeout=2,
                verify=False
            )
            http_success = response.status_code == 200
            http_response = response.json() if http_success else None
        except requests.exceptions.RequestException as e:
            http_success = False
            http_response = str(e)
            logger.error(f"HTTP test failed: {str(e)}")

        return jsonify({
            "status": "connected" if http_success else "disconnected",
            "ping_success": ping_success,
            "http_success": http_success,
            "http_response": http_response,
            "nodemcu_ip": door_controller.nodemcu_url,
            "server_ip": request.remote_addr,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Network test error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/test_connection')
def test_connection():
    """Test NodeMCU connection with detailed diagnostics"""
    try:
        # Get network interface info
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Test NodeMCU connection
        connection_status = door_controller.check_connection()
        
        return jsonify({
            "status": "success" if connection_status else "error",
            "server_info": {
                "hostname": hostname,
                "local_ip": local_ip,
                "remote_ip": request.remote_addr
            },
            "nodemcu_info": {
                "url": door_controller.nodemcu_url,
                "connected": connection_status,
                "status": door_controller.status
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Connection test error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/system_status')
def system_status():
    """Get real-time system status"""
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Get NodeMCU status
        nodemcu_status = "Disconnected"
        try:
            response = requests.get(
                f"{door_controller.nodemcu_url}/status",
                timeout=2,
                verify=False
            )
            if response.status_code == 200:
                nodemcu_status = response.json().get('status', 'Unknown')
        except requests.exceptions.RequestException:
            pass
            
        return jsonify({
            "server": {
                "ip": local_ip,
                "hostname": hostname,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "nodemcu": {
                "ip": door_controller.nodemcu_url,
                "status": nodemcu_status,
                "door_status": door_controller.status
            },
            "face_recognition": {
                "running": face_lock.running,
                "trained_faces": len(getattr(face_lock, 'known_names', []))
            }
        })
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add video feed route that was missing
@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(
        gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# Add main entry point
if __name__ == '__main__':
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Suppress TensorFlow warnings
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
        
        # Initialize video capture
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Cannot open webcam!")
            exit(1)
        cap.release()
        
        # Test NodeMCU connection
        try:
            response = requests.get(
                f"{door_controller.nodemcu_url}/status",
                timeout=2,
                verify=False
            )
            logger.info(f"NodeMCU initial connection test: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Initial NodeMCU connection test failed: {e}")
        
        # Start Flask server
        logger.info("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        
    except Exception as e:
        logger.error(f"Server startup error: {e}", exc_info=True)
    finally:
        # Cleanup
        if face_lock.running:
            face_lock.stop()