import cv2
import winsound  # Only works on Windows

def check_speed_and_overlay_image(image_path, speed):
    # Load the image
    image = cv2.imread(image_path)

    # Define the message based on speed
    if speed > 70:
        message = "Slow down speed"
        # Beep sound for overspeed
        winsound.Beep(1000, 1000)  # Frequency: 1000 Hz, Duration: 1000 ms
    else:
        message = "Speed OK"

    # Set the font and position for the message
    font = cv2.FONT_HERSHEY_SIMPLEX
    position = (50, 50)  # Top-left corner
    font_scale = 1
    color = (0, 255, 0)  # Green color
    thickness = 2

    # Overlay the message on the image
    cv2.putText(image, message, position, font, font_scale, color, thickness)

    # Display the image
    cv2.imshow("Speed Check", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Example usage
check_speed_and_overlay_image(r"C:\Users\Nisar\OneDrive\Desktop\7Speedometer\Overspeeding.jpg", 75)
