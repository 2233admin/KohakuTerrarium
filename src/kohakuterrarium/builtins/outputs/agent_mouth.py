"""
AgentMouth TTS 输出模块 — 调用本地 LuxTTS FastAPI 服务。

服务地址: http://localhost:8765/speak
接口: POST /speak {"text": "...", "voice": "..."}
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from kohakuterrarium.modules.output.base import OutputModule
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

AGENT_MOUTH_URL = "http://localhost:8765/speak"


@dataclass
class AgentMouthConfig:
    """AgentMouth 配置。"""

    url: str = AGENT_MOUTH_URL
    voice: str = "default"
    # 流式缓冲：积累到句子边界再发
    buffer_size: int = 60
    timeout: float = 10.0
    # 只播报指定前缀内容（空=全播）
    prefix_filter: str = ""
    options: dict[str, Any] = field(default_factory=dict)


class AgentMouthOutput(OutputModule):
    """
    AgentMouth TTS 输出。

    将 agent 文本输出转发到本地 LuxTTS 服务（:8765）异步播报。
    支持流式缓冲，按句子边界触发发音，不阻塞主流程。
    """

    def __init__(self, config: AgentMouthConfig | None = None):
        self.config = config or AgentMouthConfig()
        self._buffer = ""
        self._session: aiohttp.ClientSession | None = None
        self._speak_task: asyncio.Task | None = None

    async def start(self) -> None:
        """初始化 HTTP 会话。"""
        self._session = aiohttp.ClientSession()
        logger.info("AgentMouth output started", url=self.config.url)

    async def stop(self) -> None:
        """关闭 HTTP 会话。"""
        # 等待正在播报的任务
        if self._speak_task and not self._speak_task.done():
            try:
                await asyncio.wait_for(self._speak_task, timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                pass

        if self._session:
            await self._session.close()
            self._session = None
        logger.info("AgentMouth output stopped")

    async def write(self, text: str) -> None:
        """写入完整文本，直接播报。"""
        if not text.strip():
            return
        await self._fire_and_forget(text)

    async def write_stream(self, chunk: str) -> None:
        """流式写入，缓冲到句子边界再播报。"""
        self._buffer += chunk

        should_flush = (
            len(self._buffer) >= self.config.buffer_size
            or self._ends_sentence(self._buffer)
        )

        if should_flush and self._buffer.strip():
            text = self._buffer
            self._buffer = ""
            await self._fire_and_forget(text)

    async def flush(self) -> None:
        """强制播报剩余缓冲内容。"""
        if self._buffer.strip():
            text = self._buffer
            self._buffer = ""
            await self._fire_and_forget(text)

    async def _fire_and_forget(self, text: str) -> None:
        """
        后台发送 TTS 请求，不阻塞调用方。
        前一个 speak 任务未完成时直接覆盖（不排队）。
        """
        self._speak_task = asyncio.create_task(self._post_speak(text))

    async def _post_speak(self, text: str) -> None:
        """POST /speak 请求。失败静默 log，不抛异常。"""
        if self._session is None:
            logger.warning("AgentMouth: session not started, skipping speak")
            return

        payload = {"text": text, "voice": self.config.voice, **self.config.options}
        try:
            async with self._session.post(
                self.config.url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        "AgentMouth speak failed",
                        status=resp.status,
                        body=body[:200],
                    )
                else:
                    logger.debug("AgentMouth spoke", text_len=len(text))
        except aiohttp.ClientConnectorError:
            logger.warning("AgentMouth: LuxTTS not reachable at %s", self.config.url)
        except asyncio.TimeoutError:
            logger.warning("AgentMouth: speak timeout", text_len=len(text))
        except Exception as e:
            logger.error("AgentMouth unexpected error", error=str(e))

    @staticmethod
    def _ends_sentence(text: str) -> bool:
        """是否以句子边界结尾。"""
        t = text.rstrip()
        return bool(t) and t[-1] in ".!?。！？…\n"
