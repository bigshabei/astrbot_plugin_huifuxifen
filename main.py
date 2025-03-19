import os
import traceback
import time
import asyncio
import json
import builtins
import random
import re
from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

@register("astrbot_plugin_huifuxifen", "大沙北", "主动回复管理插件", "1.1.0")
class ActiveReplyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        # 从配置中读取回复概率
        self.reply_rates = self.config.get('active_reply_rates', {})
        # 从配置中读取插件开关状态
        self.plugin_enabled = self.config.get('plugin_enabled', True)
        # 别问，问就是我也不知道咋用
        self.regex_commands = self.config.get('regex_commands', {})

    @filter.command("设置群回复率")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def set_group_reply_rate(self, event: AstrMessageEvent, 群ID: str, 概率: float):
        if not self.plugin_enabled:
            yield event.plain_result("插件已关闭，无法执行此操作。")
            return
        if 0 <= 概率 <= 1:
            if 'groups' not in self.reply_rates:
                self.reply_rates['groups'] = {}
            self.reply_rates['groups'][群ID] = 概率
            # 保存配置
            self.config['active_reply_rates'] = self.reply_rates
            self.config.save_config()
            yield event.plain_result(f"已设置群 {群ID} 的回复概率为 {概率}")
        else:
            yield event.plain_result("概率必须在0到1之间")

    @filter.command("设置用户回复率")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def set_user_reply_rate(self, event: AstrMessageEvent, 群ID: str, 用户ID: str, 概率: float):
        if not self.plugin_enabled:
            yield event.plain_result("插件已关闭，无法执行此操作。")
            return
        if 0 <= 概率 <= 1:
            if 'users' not in self.reply_rates:
                self.reply_rates['users'] = {}
            if 群ID not in self.reply_rates['users']:
                self.reply_rates['users'][群ID] = {}
            self.reply_rates['users'][群ID][用户ID] = 概率
            # 保存配置
            self.config['active_reply_rates'] = self.reply_rates
            self.config.save_config()
            yield event.plain_result(f"已设置群 {群ID} 中用户 {用户ID} 的回复概率为 {概率}")
        else:
            yield event.plain_result("概率必须在0到1之间")

    @filter.command("移除用户回复率")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def remove_user_reply_rate(self, event: AstrMessageEvent, 群ID: str, 用户ID: str):
        if not self.plugin_enabled:
            yield event.plain_result("插件已关闭，无法执行此操作。")
            return
        if 'users' in self.reply_rates and 群ID in self.reply_rates['users'] and 用户ID in self.reply_rates['users'][群ID]:
            del self.reply_rates['users'][群ID][用户ID]
            # 保存配置
            self.config['active_reply_rates'] = self.reply_rates
            self.config.save_config()
            yield event.plain_result(f"已移除群 {群ID} 中用户 {用户ID} 的回复概率设置")
        else:
            yield event.plain_result("未找到该用户的回复概率设置")

    @filter.command("删除群回复率")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def delete_group_reply_rate(self, event: AstrMessageEvent, 群ID: str):
        if not self.plugin_enabled:
            yield event.plain_result("插件已关闭，无法执行此操作。")
            return
        if 'groups' in self.reply_rates and 群ID in self.reply_rates['groups']:
            del self.reply_rates['groups'][群ID]
            # 保存配置
            self.config['active_reply_rates'] = self.reply_rates
            self.config.save_config()
            yield event.plain_result(f"已删除群 {群ID} 的回复概率设置")
        else:
            yield event.plain_result("未找到该群的回复概率设置")

    @filter.command("主动回复列表")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def list_reply_rates(self, event: AstrMessageEvent):
        if not self.plugin_enabled:
            yield event.plain_result("插件已关闭，无法执行此操作。")
            return
        result = "群回复概率设置:\n"
        for group_id, rate in self.reply_rates.get('groups', {}).items():
            result += f"群 {group_id}: {rate}\n"
        
        result += "\n用户回复概率设置:\n"
        for group_id, users in self.reply_rates.get('users', {}).items():
            for user_id, rate in users.items():
                result += f"群 {group_id} 用户 {user_id}: {rate}\n"
        
        yield event.plain_result(result if result != "" else "没有设置任何回复概率")

    @filter.command("主动回复帮助")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def help(self, event: AstrMessageEvent):
        help_text = """
主动回复插件帮助:
- /设置群回复率 <群ID> <概率>: 设置群聊的回复概率，概率在0到1之间。
- /设置用户回复率 <群ID> <用户ID> <概率>: 设置特定群聊中特定用户的回复概率，概率在0到1之间。
- /移除用户回复率 <群ID> <用户ID>: 移除特定群聊内用户的回复概率设置。
- /删除群回复率 <群ID>: 删除群聊的回复概率设置。
- /主动回复列表: 查看所有设置的回复概率。
- /主动回复帮助: 显示此帮助信息。
- /获取群ID: 获取当前群ID和发送者用户ID。
- /开启主动回复: 开启主动回复插件。
- /关闭主动回复: 关闭主动回复插件。
        """
        yield event.plain_result(help_text)

    @filter.command("获取群ID")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def get_group_id(self, event: AstrMessageEvent):
        """获取当前群ID并携带发送此命令的用户ID"""
        if not self.plugin_enabled:
            yield event.plain_result("插件已关闭，无法执行此操作。")
            return
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        if group_id:
            yield event.plain_result(f"当前群ID: {group_id}, 发送者用户ID: {user_id}")
        else:
            yield event.plain_result("这不是群聊消息，无法获取群ID。")

    @filter.command("开启主动回复")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def enable_plugin(self, event: AstrMessageEvent):
        self.plugin_enabled = True
        self.config['plugin_enabled'] = True
        self.config.save_config()
        yield event.plain_result("主动回复插件已开启。")

    @filter.command("关闭主动回复")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def disable_plugin(self, event: AstrMessageEvent):
        self.plugin_enabled = False
        self.config['plugin_enabled'] = False
        self.config.save_config()
        yield event.plain_result("主动回复插件已关闭。")

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """处理群消息事件"""
        if not self.plugin_enabled:
            return

        group_id = event.get_group_id()
        user_id = event.get_sender_id()

        # 检查是否为插件指令
        if event.is_at_or_wake_command:
            # 如果是指令，不触发LLM
            return

        # 别问，不会用
        for command, pattern in self.regex_commands.items():
            if re.match(pattern, event.message_str):
                return

        # 获取群和用户的回复概率
        group_rate = self.reply_rates.get('groups', {}).get(str(group_id), 0.0)
        user_rate = self.reply_rates.get('users', {}).get(str(group_id), {}).get(str(user_id), None)

        # 决定是否触发LLM调用
        # 优先调用用户概率
        trigger_rate = user_rate if user_rate is not None else group_rate

        if random.random() < trigger_rate:
            # 设置唤醒命令，确保使用现有会话
            event.is_at_or_wake_command = True

            # 使用现有对话
            curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin)
            conversation = None
            if curr_cid:
                conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)

            # 触发LLM
            yield event.request_llm(
                prompt=event.message_str,
                func_tool_manager=self.context.get_llm_tool_manager(),
                session_id=curr_cid,
                conversation=conversation,
            )
