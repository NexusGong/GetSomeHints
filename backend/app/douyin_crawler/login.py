# -*- coding: utf-8 -*-
"""抖音登录（二维码 / Cookie / 手机，仅供学习研究）。"""
import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed

from app.douyin_crawler import config as config_module
from app.douyin_crawler.utils import (
    Slide,
    convert_cookies,
    convert_str_cookie_to_dict,
    find_login_qrcode,
    get_tracks,
    logger,
    show_qrcode,
)


class DouYinLogin:
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: Optional[str] = "",
    ):
        config_module.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.scan_qrcode_time = 60
        self.cookie_str = cookie_str or ""

    async def begin(self) -> None:
        await self.popup_login_dialog()
        if config_module.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config_module.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config_module.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[DouYinLogin.begin] Invalid Login Type (qrcode | phone | cookie)")

        await asyncio.sleep(6)
        title = await self.context_page.title()
        if "验证码中间页" in title:
            await self.check_page_display_slider(move_step=3, slider_level="hard")

        logger.info("[DouYinLogin.begin] login finished then check login state ...")
        try:
            await self.check_login_state()
        except RetryError:
            logger.warning("[DouYinLogin.begin] login failed please confirm ...")
            sys.exit(1)
        await asyncio.sleep(5)

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda v: v is False))
    async def check_login_state(self) -> bool:
        cookies = await self.browser_context.cookies()
        _, cookie_dict = convert_cookies(cookies)
        for page in self.browser_context.pages:
            try:
                local = await page.evaluate("() => window.localStorage")
                if local.get("HasUserLogin", "") == "1":
                    return True
            except Exception:
                await asyncio.sleep(0.1)
        if cookie_dict.get("LOGIN_STATUS") == "1":
            return True
        return False

    async def popup_login_dialog(self) -> None:
        selector = "xpath=//div[@id='login-panel-new']"
        try:
            await self.context_page.wait_for_selector(selector, timeout=10000)
        except Exception as e:
            logger.error("[DouYinLogin.popup_login_dialog] %s", e)
            btn = self.context_page.locator("xpath=//p[text() = '登录']")
            await btn.click()
            await asyncio.sleep(0.5)

    async def login_by_qrcode(self) -> None:
        logger.info("[DouYinLogin.login_by_qrcode] Begin login douyin by qrcode...")
        selector = "xpath=//div[@id='animate_qrcode_container']//img"
        base64_img = await find_login_qrcode(self.context_page, selector=selector)
        if not base64_img:
            logger.error("[DouYinLogin.login_by_qrcode] qrcode not found")
            sys.exit(1)
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, functools.partial(show_qrcode, base64_img))
        await asyncio.sleep(2)

    async def login_by_mobile(self) -> None:
        logger.info("[DouYinLogin.login_by_mobile] Begin login douyin by mobile ...")
        await self.context_page.locator("xpath=//li[text() = '验证码登录']").click()
        await self.context_page.wait_for_selector("xpath=//article[@class='web-login-mobile-code']")
        await self.context_page.locator("xpath=//input[@placeholder='手机号']").fill(self.login_phone)
        await asyncio.sleep(0.5)
        await self.context_page.locator("xpath=//span[text() = '获取验证码']").click()
        await self.check_page_display_slider(move_step=10, slider_level="easy")
        # 无 Redis/Cache 时仅轮询占位，实际需自行接入验证码
        for _ in range(120):
            await asyncio.sleep(1)
            logger.info("[DouYinLogin.login_by_mobile] waiting for sms code (no cache configured) ...")

    async def check_page_display_slider(self, move_step: int = 10, slider_level: str = "easy") -> None:
        back_selector = "#captcha-verify-image"
        try:
            await self.context_page.wait_for_selector(back_selector, state="visible", timeout=30000)
        except PlaywrightTimeoutError:
            return
        gap_selector = "xpath=//*[@id='captcha_container']/div/div[2]/img[2]"
        max_tries = 20
        for _ in range(max_tries):
            try:
                await self.move_slider(back_selector, gap_selector, move_step, slider_level)
                await asyncio.sleep(1)
                content = await self.context_page.content()
                if "操作过慢" in content or "提示重新操作" in content:
                    await self.context_page.click("//a[contains(@class, 'secsdk_captcha_refresh')]")
                    continue
                await self.context_page.wait_for_selector(back_selector, state="hidden", timeout=1000)
                logger.info("[DouYinLogin.check_page_display_slider] slider verify success ...")
                return
            except Exception as e:
                logger.warning("[DouYinLogin.check_page_display_slider] %s", e)
                await asyncio.sleep(1)
        logger.error("[DouYinLogin.check_page_display_slider] slider verify failed ...")
        sys.exit(1)

    async def move_slider(
        self, back_selector: str, gap_selector: str, move_step: int = 10, slider_level: str = "easy"
    ) -> None:
        back_el = await self.context_page.wait_for_selector(back_selector, timeout=10000)
        slide_back = str(await back_el.get_property("src"))
        gap_el = await self.context_page.wait_for_selector(gap_selector, timeout=10000)
        gap_src = str(await gap_el.get_property("src"))
        slide_app = Slide(gap=gap_src, bg=slide_back)
        distance = slide_app.discern()
        tracks = get_tracks(distance, slider_level)
        if tracks:
            new_last = tracks[-1] - (sum(tracks) - distance)
            tracks = tracks[:-1] + [new_last]
        el = await self.context_page.query_selector(gap_selector)
        box = await el.bounding_box()
        if not box:
            return
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        await self.context_page.mouse.move(x, y)
        await el.hover()
        await self.context_page.mouse.down()
        for t in tracks:
            await self.context_page.mouse.move(x + t, y, steps=move_step)
            x += t
        await self.context_page.mouse.up()

    async def login_by_cookies(self) -> None:
        logger.info("[DouYinLogin.login_by_cookies] Begin login by cookie ...")
        for k, v in convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies(
                [{"name": k, "value": v, "domain": ".douyin.com", "path": "/"}]
            )
