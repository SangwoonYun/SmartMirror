import io
import time
import base64
from PIL import Image
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


BASE = 'https://sports.daum.net'
SCHEDULE_SEL = '#cSub > div.feature_top > div.top_sched > div.bundle_sched.bundle_baseball'
TARGET_SEL = (
    '#kakaoWrap > main > div > div:nth-child(1) > '
    'div.box_comp.box_cast > div.broadcast_field > '
    'div.group_diamond > ul:nth-child(4)'
)
HEADLESS_MODE = 'new'
VIEW_W, VIEW_H = 1920, 1080
DPR = 2


def wait_dom_fonts_images(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script('return document.readyState') == 'complete'
    )
    try:
        WebDriverWait(driver, min(timeout, 8)).until(
            lambda d: d.execute_script(
                'return (document.fonts && document.fonts.status==='loaded') || !document.fonts'
            )
        )
    except Exception:
        pass
    try:
        WebDriverWait(driver, min(timeout, 10)).until(
            lambda d: d.execute_script(
                'return Array.from(document.images).every(i => i.complete && i.naturalWidth>0)'
            )
        )
    except Exception:
        pass


def kill_css_blur(driver):
    driver.execute_script(
        """
        const style = document.createElement('style');
        style.id = '___anti_blur_style';
        style.innerHTML = `
          * {
            filter: none !important;
            -webkit-filter: none !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            image-rendering: auto !important;
          }
          html, body { zoom: 1 !important; }
        `;
        document.head.appendChild(style);
        """
    )


def wait_high_res_images(driver, min_width=800, timeout=0.5):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                """
                const imgs = Array.from(document.images);
                if (!imgs.length) return true;
                return imgs.every(img => img.complete && img.naturalWidth >= arguments[0]);
                """,
                min_width
            )
        )
    except Exception:
        pass


def stabilize_layout(driver):
    driver.execute_script(
        f"""
        const H = Math.max(
          document.body.scrollHeight, document.documentElement.scrollHeight,
          document.body.offsetHeight, document.documentElement.offsetHeight
        );
        const step = Math.max(400, {VIEW_H} * 0.8);
        let y = 0;
        function jump(t){{ window.scrollTo({{top:t, behavior:'instant'}}); }}
        while (y < H) {{ jump(y); y += step; }}
        jump(0);
        """
    )
    time.sleep(0.4)


def element_rect_with_dpr(driver, css_selector):
    return driver.execute_script(
        """
        const el = document.querySelector(arguments[0]);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        return {x:r.x, y:r.y, w:r.width, h:r.height, dpr:dpr};
        """,
        css_selector
    )


def viewport_png_bytes(driver):
    b64 = driver.get_screenshot_as_base64()
    return base64.b64decode(b64)


def crop_by_rect(png_bytes, rect):
    img = Image.open(io.BytesIO(png_bytes))
    left   = max(0, int(rect['x'] * rect['dpr']))
    top    = max(0, int(rect['y'] * rect['dpr']))
    right  = min(img.width,  left + int(rect['w'] * rect['dpr']))
    bottom = min(img.height, top  + int(rect['h'] * rect['dpr']))
    if right <= left or bottom <= top:
        raise RuntimeError(f'invalid crop box: {(left, top, right, bottom)}')
    return img.crop((left, top, right, bottom))


def capture_stable_element(
        driver,
        css_selector,
        out_path,
        wait_timeout=20,
        attempts=4,
        min_bytes=4000
):
    WebDriverWait(driver, wait_timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
    )
    WebDriverWait(driver, wait_timeout).until(
        lambda d: d.execute_script(
            """
            const el = document.querySelector(arguments[0]);
            if (!el) return false;
            const st = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return st.display!=='none' && st.visibility!=='hidden' && r.width>10 && r.height>10;
            """,
            css_selector
        )
    )

    el = driver.find_element(By.CSS_SELECTOR, css_selector)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.2)
    stabilize_layout(driver)

    last_err = None
    for i in range(1, attempts + 1):
        try:
            wait_dom_fonts_images(driver, timeout=min(wait_timeout, 12))
            kill_css_blur(driver)
            wait_high_res_images(driver, 900)

            rect = element_rect_with_dpr(driver, css_selector)
            if not rect or rect['w'] < 2 or rect['h'] < 2:
                raise RuntimeError('element rect is invalid/too small')

            png = viewport_png_bytes(driver)
            if len(png) < min_bytes:
                raise RuntimeError(f'viewport screenshot too small: {len(png)} bytes')

            img = crop_by_rect(png, rect)

            # 유효성 체크
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            raw = buf.getvalue()
            if len(raw) < 1500 or img.width < 32 or img.height < 32:
                raise RuntimeError(f'cropped image seems invalid: {img.size}, {len(raw)} bytes')

            with open(out_path, 'wb') as f:
                f.write(raw)
            return out_path

        except Exception as e:
            last_err = e
            time.sleep(0.5 * i)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.2)
            stabilize_layout(driver)

    with open('__debug_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    with open('__debug_viewport.png', 'wb') as f:
        f.write(viewport_png_bytes(driver))

    raise RuntimeError(f'capture failed after {attempts} attempts: {last_err}')


def get_soup(css_selector, driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    except Exception:
        pass
    return BeautifulSoup(driver.page_source, 'html.parser')


def make_driver():
    options = Options()
    if HEADLESS_MODE == 'new':
        options.add_argument('--headless=new')
    else:
        options.add_argument('--headless')

    options.add_argument(f'--window-size={VIEW_W},{VIEW_H}')
    options.add_argument('--hide-scrollbars')
    options.add_argument(f'--force-device-scale-factor={DPR}')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
        'mobile': False,
        'width': VIEW_W,
        'height': VIEW_H,
        'deviceScaleFactor': DPR
    })
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    except Exception:
        pass

    try:
        driver.execute_script("document.body.style.zoom='1'; document.documentElement.style.zoom='1';")
    except Exception:
        pass

    return driver


def dismiss_unknown_error_popup(driver, timeout=3):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.popup_layer, div.dimmed_layer.on'))
        )
    except TimeoutException:
        return False

    try:
        msg = driver.find_element(By.CSS_SELECTOR, 'div.popup_layer .txt_comm').text
    except Exception:
        msg = ''

    if '알 수 없는 오류가 발생했습니다' in msg or True:
        try:
            btn = WebDriverWait(driver, 1.5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[contains(@class,'popup_layer')]"
                    "//button[.//span[contains(normalize-space(.),'확인')] or contains(@class,'btn_g')]"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.1)
            try:
                btn.click()
            except Exception:
                driver.execute_script('arguments[0].click();', btn)
        except TimeoutException:
            pass

        try:
            WebDriverWait(driver, 2).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, 'div.popup_layer')) == 0
            )
            return True
        except TimeoutException:
            return False
    return False


def nuke_modal_overlays(driver):
    driver.execute_script(
        """
        document.querySelectorAll('.popup_layer, .dimmed_layer.on')
                .forEach(e => e.remove());
        document.body.style.overflow = 'auto';
        """
    )


def main():
    driver = make_driver()
    try:
        driver.get(f'{BASE}/baseball/')
        wait_dom_fonts_images(driver)
        kill_css_blur(driver)
        stabilize_layout(driver)

        soup = get_soup(SCHEDULE_SEL, driver)
        schedule = soup.select_one(SCHEDULE_SEL)
        if not schedule:
            raise RuntimeError('schedule block not found')

        links = [a.get('href') for a in schedule.find_all('a', recursive=False) if a.get('href')]
        if not links:
            links = [a.get('href') for a in schedule.select('a[href]')]
        if not links:
            raise RuntimeError('no links found in schedule block')

        for idx, uri in enumerate(links, start=1):
            url = uri if uri.startswith('http') else f'{BASE}{uri}'
            driver.get(url)
            wait_dom_fonts_images(driver)
            kill_css_blur(driver)
            wait_high_res_images(driver, 900)
            stabilize_layout(driver)

            out = f'cast_section_{idx}.png'
            try:
                if not dismiss_unknown_error_popup(driver, timeout=2):
                    nuke_modal_overlays(driver)
                capture_stable_element(driver, TARGET_SEL, out_path=out, attempts=4)
            except Exception as e:
                print(f'❌ Capture fail({idx}): {e}')

    finally:
        driver.quit()


if __name__ == '__main__':
    main()
