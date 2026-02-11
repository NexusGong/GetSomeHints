# -*- coding: utf-8 -*-
"""小红书登录（二维码 / Cookie / 手机，不依赖 bundle cache）。"""
import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed

from app.xhs_crawler import config as xhs_config
from app.xhs_crawler.utils import convert_cookies, convert_str_cookie_to_dict, logger, show_qrcode, find_login_qrcode

# 手机验证码缓存：外部可写入 xhs_crawler.login.sms_code_cache[phone] = code
sms_code_cache: dict = {}


class XiaoHongShuLogin:
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = "",
    ):
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone or ""
        self.cookie_str = cookie_str
        self._login_type = login_type

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        try:
            user_profile_selector = "xpath=//a[contains(@href, '/user/profile/')]//span[text()='我']"
            is_visible = await self.context_page.is_visible(user_profile_selector, timeout=500)
            if is_visible:
                logger.info("[XiaoHongShuLogin.check_login_state] Login status confirmed by UI element.")
                return True
        except Exception:
            pass
        if "请通过验证" in await self.context_page.content():
            logger.info("[XiaoHongShuLogin.check_login_state] CAPTCHA appeared, please verify manually.")
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = convert_cookies(current_cookie)
        current_web_session = cookie_dict.get("web_session")
        if current_web_session and current_web_session != no_logged_in_session:
            logger.info("[XiaoHongShuLogin.check_login_state] Login status confirmed by Cookie.")
            return True
        return False

    async def begin(self) -> None:
        logger.info("[XiaoHongShuLogin.begin] Begin login xiaohongshu ...")
        if self._login_type == "qrcode":
            await self.login_by_qrcode()
        elif self._login_type == "phone":
            await self.login_by_mobile()
        elif self._login_type == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[XiaoHongShuLogin.begin] Invalid Login Type. Supported: qrcode, phone, cookie.")

    async def login_by_mobile(self) -> None:
        logger.info("[XiaoHongShuLogin.login_by_mobile] Begin login xiaohongshu by mobile ...")
        await asyncio.sleep(1)
        try:
            login_button_ele = await self.context_page.wait_for_selector(
                selector="xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button",
                timeout=5000,
            )
            await login_button_ele.click()
            element = await self.context_page.wait_for_selector(
                selector='xpath=//div[@class="login-container"]//div[@class="other-method"]/div[1]',
                timeout=5000,
            )
            await element.click()
        except Exception:
            pass
        await asyncio.sleep(1)
        login_container_ele = await self.context_page.wait_for_selector("div.login-container")
        input_ele = await login_container_ele.query_selector("label.phone > input")
        await input_ele.fill(self.login_phone)
        await asyncio.sleep(0.5)
        send_btn_ele = await login_container_ele.query_selector("label.auth-code > span")
        await send_btn_ele.click()
        sms_code_input_ele = await login_container_ele.query_selector("label.auth-code > input")
        submit_btn_ele = await login_container_ele.query_selector("div.input-container > button")
        no_logged_in_session = ""
        max_wait = 120
        while max_wait > 0:
            code = sms_code_cache.get(self.login_phone)
            if code:
                current_cookie = await self.browser_context.cookies()
                _, cookie_dict = convert_cookies(current_cookie)
                no_logged_in_session = cookie_dict.get("web_session", "")
                await sms_code_input_ele.fill(value=code)
                await asyncio.sleep(0.5)
                agree_privacy_ele = self.context_page.locator("xpath=//div[@class='agreements']//*[local-name()='svg']")
                await agree_privacy_ele.click()
                await asyncio.sleep(0.5)
                await submit_btn_ele.click()
                break
            await asyncio.sleep(1)
            max_wait -= 1
        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            logger.info("[XiaoHongShuLogin.login_by_mobile] Login xiaohongshu failed by mobile.")
            sys.exit(1)
        await asyncio.sleep(5)

    async def login_by_qrcode(self) -> None:
        logger.info("[XiaoHongShuLogin.login_by_qrcode] Begin login xiaohongshu by qrcode ...")
        qrcode_img_selector = "xpath=//img[@class='qrcode-img']"
        base64_qrcode_img = await find_login_qrcode(self.context_page, selector=qrcode_img_selector)
        if not base64_qrcode_img:
            await asyncio.sleep(0.5)
            login_button_ele = self.context_page.locator("xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button")
            await login_button_ele.click()
            base64_qrcode_img = await find_login_qrcode(self.context_page, selector=qrcode_img_selector)
            if not base64_qrcode_img:
                sys.exit(1)
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("web_session", "")
        partial_show_qrcode = functools.partial(show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)
        logger.info("[XiaoHongShuLogin.login_by_qrcode] waiting for scan code login, remaining time is 120s")
        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            logger.info("[XiaoHongShuLogin.login_by_qrcode] Login xiaohongshu failed by qrcode.")
            sys.exit(1)
        await asyncio.sleep(5)

    async def login_by_cookies(self) -> None:
        logger.info("[XiaoHongShuLogin.login_by_cookies] Begin login xiaohongshu by cookie ...")
        for key, value in convert_str_cookie_to_dict(self.cookie_str).items():
            if key != "web_session":
                continue
            await self.browser_context.add_cookies(
                [
                    {
                        "name": key,
                        "value": value,
                        "domain": ".xiaohongshu.com",
                        "path": "/",
                    }
                ]
            )
