import io
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image

# ── Configuration ──────────────────────────────────────────────────────────────
CANVAS_WIDTH  = 1500
CANVAS_HEIGHT = 370

CAPTURE_DURATION_S  = 14       # Full 14s typing cycle
FRAME_INTERVAL_MS   = 100      # 100ms -> 10 fps
INITIAL_WAIT_S      = 3        # Wait for fonts/CSS to load

def generate_gif():
    html_path       = "file:///" + os.path.abspath("assets/animations/banner.html").replace("\\", "/")
    output_gif_path = os.path.abspath("assets/banner.gif")
    
    print(f"Loading HTML : {html_path}")
    print(f"Output GIF   : {output_gif_path}")
    print(f"Canvas       : {CANVAS_WIDTH}x{CANVAS_HEIGHT}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--hide-scrollbars")
    options.add_argument(f"--window-size={CANVAS_WIDTH},{CANVAS_HEIGHT}")
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(CANVAS_WIDTH, CANVAS_HEIGHT)
    
    try:
        driver.get(html_path)
        print(f"Waiting {INITIAL_WAIT_S}s for fonts & animations...")
        time.sleep(INITIAL_WAIT_S)

        total_frames = (CAPTURE_DURATION_S * 1000) // FRAME_INTERVAL_MS
        frames       = []

        print(f"Capturing {total_frames} frames...")
        for i in range(total_frames):
            png_data    = driver.get_screenshot_as_png()
            img         = Image.open(io.BytesIO(png_data))
            img_cropped = img.crop((0, 0, CANVAS_WIDTH, CANVAS_HEIGHT))
            frames.append(img_cropped.convert("P", palette=Image.ADAPTIVE, colors=256))

            if i < total_frames - 1:
                time.sleep(FRAME_INTERVAL_MS / 1000.0)

        print("Saving looping GIF...")
        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=FRAME_INTERVAL_MS,
            loop=0,
            optimize=True
        )
        print(f"✓ GIF generated successfully -> {output_gif_path}")

    except Exception as e:
        print(f"✗ Error during GIF generation: {e}")
        raise
    finally:
        driver.quit()

if __name__ == "__main__":
    generate_gif()
