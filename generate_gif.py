import io
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image

def generate_gif():
    # Paths
    html_path = "file:///" + os.path.abspath("assets/animations/banner.html").replace("\\", "/")
    output_gif_path = os.path.abspath("assets/banner.gif")
    
    print(f"Loading HTML from: {html_path}")
    print(f"Generating GIF to: {output_gif_path}")

    # Set up headless Chrome
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1000,400")
    
    # Locate Chrome binary on Windows
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    # Start WebDriver
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1000, 400)
    
    try:
        # Load the page
        driver.get(html_path)
        # Wait for Google Fonts to load
        time.sleep(3)

        frames = []
        total_duration = 5000  # 5.0 seconds
        frame_interval = 100   # 100ms per frame (10 fps)

        print("Capturing frames...")
        for t in range(0, total_duration, frame_interval):
            # Render the frame for time t (in ms)
            driver.execute_script(f"setFrame({t})")
            
            # Take screenshot as PNG bytes
            png_data = driver.get_screenshot_as_png()
            
            # Open as PIL Image and convert to RGB
            img = Image.open(io.BytesIO(png_data))
            img_rgb = img.convert("RGB")
            frames.append(img_rgb)
            
            if (t + frame_interval) % 1000 == 0:
                print(f"  Captured {t + frame_interval}ms / {total_duration}ms")

        # Save as looping GIF
        print("Saving looping GIF...")
        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_interval,
            loop=0,
            optimize=True
        )
        print("GIF generated successfully!")

    except Exception as e:
        print(f"Error during GIF generation: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    generate_gif()
