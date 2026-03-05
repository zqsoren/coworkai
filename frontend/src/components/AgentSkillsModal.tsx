import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Wrench, Zap, Loader2, Plug, Plus, Edit2, X, ChevronDown, ChevronUp, Store, Search, Check, ExternalLink } from "lucide-react"
import { useStore } from "@/store"
import { useEffect, useState, useMemo } from "react"
import { fetchSkills, fetchTools, registerFeishu } from "@/lib/api"
import yingmiIcon from "@/assets/icons/yingmi.png"
import tianyanchaIcon from "@/assets/icons/tianyancha.png"
import investodayIcon from "@/assets/icons/investoday.png"
import tencentFinanceIcon from "@/assets/icons/tencent_finance.png"
import firstdataIcon from "@/assets/icons/firstdata.png"
import tavilyIcon from "@/assets/icons/tavily.png"
import feishuIcon from "@/assets/icons/feishu.png"
import xiaohongshuIcon from "@/assets/icons/xiaohongshu.png"


interface AgentSkillsModalProps {
    open: boolean
    onOpenChange: (open: boolean) => void
}

interface ToolInfo {
    name: string
    label: string
    group: string
    description: string
}

interface SkillInfo {
    name: string
    description: string
}

interface MCPServerConfig {
    id: string
    name: string
    transport: "stdio" | "sse" | "http"
    command: string
    args: string[]
    env: Record<string, string>
    url: string
    api_key: string
    headers: Record<string, string>
    description?: string
    icon?: string
    enabled: boolean
}

export const TOOL_LABELS: Record<string, string> = {
    "read_file": "读取文件",
    "write_file": "写入文件",
    "list_directory": "列出目录",
    "move_file": "移动文件",
    "get_file_diff": "文件对比",
    "google_search": "搜索引擎",
    "fetch_url_content": "抓取网页",
    "python_repl": "Python 执行器",
    "get_current_time": "获取当前时间",
    "take_screenshot": "屏幕截图",
    "open_browser": "打开浏览器",
    "get_page_text": "获取页面文本",
    "page_screenshot": "页面截图",
    "scroll_page": "滚动页面",
    "check_login_status": "检测登录状态",
    "wait_for_login": "等待扫码登录",
    "close_browser": "关闭浏览器",
    "create_new_agent": "创建新Agent",
    "list_available_agents": "列出所有Agent",
    "read_any_file": "读取任意文件",
    "search_files_by_keyword": "关键词搜索文件",
    "suggest_delegation_to_agent": "委派任务给Agent",
    "search_knowledge_base": "知识库检索",
    "get_realtime_stock_data": "实时股价查询",
    "search_stock_by_name": "股票代码搜索",
}

// 系统默认工具 - 所有 Agent 自动拥有，不在 UI 中显示
const SYSTEM_DEFAULT_TOOLS = new Set([
    "read_file", "write_file", "list_directory", "move_file", "get_file_diff",
    "google_search", "fetch_url_content", "python_repl", "get_current_time",
    "take_screenshot", "open_browser", "get_page_text", "page_screenshot",
    "scroll_page", "check_login_status", "wait_for_login", "close_browser",
    "search_files_by_keyword", "shell_command",
    "create_scheduled_task", "list_scheduled_tasks", "delete_scheduled_task",
])

// Meta-Agent 专属工具 - 仅超级助手拥有，普通 Agent 不显示
const META_AGENT_TOOLS = new Set([
    "list_all_files_recursive", "read_any_file", "list_available_agents",
])

export const SKILL_LABELS: Record<string, string> = {
    "browser_takeover": "浏览器接管",
    "data_viz": "数据可视化",
    "deep_research": "深度研究",
    "xhs_scraper": "小红书数据采集",
    "mcp_builder": "MCP 服务器开发",
    "skill_creator": "技能创建者",
    "portfolio_manager": "个人持仓管理",
}

const POPULAR_MCP_SERVERS = [
    { name: "filesystem", transport: "stdio" as const, command: "npx", args: ["-y", "@anthropic-ai/mcp-server-filesystem"], description: "文件系统访问" },
    { name: "github", transport: "stdio" as const, command: "npx", args: ["-y", "@anthropic-ai/mcp-server-github"], description: "GitHub API", env: { "GITHUB_TOKEN": "" } },
    { name: "postgres", transport: "stdio" as const, command: "npx", args: ["-y", "@anthropic-ai/mcp-server-postgres"], description: "PostgreSQL 数据库" },
    { name: "puppeteer", transport: "stdio" as const, command: "npx", args: ["-y", "@anthropic-ai/mcp-server-puppeteer"], description: "浏览器自动化" },
    { name: "slack", transport: "stdio" as const, command: "npx", args: ["-y", "@anthropic-ai/mcp-server-slack"], description: "Slack 集成", env: { "SLACK_BOT_TOKEN": "" } },
    { name: "brave-search", transport: "stdio" as const, command: "npx", args: ["-y", "@anthropic-ai/mcp-server-brave-search"], description: "Brave 搜索", env: { "BRAVE_API_KEY": "" } },
]

const MCP_MARKET_CATEGORIES = ["全部", "企业服务", "金融服务", "行情数据", "数据服务", "搜索服务", "智能技能", "消息通道"] as const

export const MCP_MARKET_ITEMS = [
    {
        id: "tianyancha",
        name: "天眼查",
        description: "企业信息查询、工商数据、风险分析等企业服务",
        icon: tianyanchaIcon,
        type: "mcp" as const,
        transport: "sse" as const,
        url: "https://mcp-service.tianyancha.com/sse",
        httpUrl: "https://mcp-service.tianyancha.com/mcp",
        requiresApiKey: true,
        apiKeyPlaceholder: "请输入天眼查 API Key",
        category: "企业服务",
        apiKeyUrl: "https://mcp.tianyancha.com/"
    },
    {
        id: "yingmi",
        name: "盈米基金",
        description: "基金数据查询、投资组合分析等金融服务",
        icon: yingmiIcon,
        type: "mcp" as const,
        transport: "sse" as const,
        url: "https://stargate.yingmi.com/mcp/sse",
        requiresApiKey: true,
        apiKeyPlaceholder: "请输入盈米基金 API Key",
        category: "金融服务",
        apiKeyUrl: "https://qieman.com/mcp/service-ativation?state="
    },
    {
        id: "investoday",
        name: "今日投资",
        description: "投资数据、市场分析、财经资讯等数据服务",
        icon: investodayIcon,
        type: "mcp" as const,
        transport: "sse" as const,
        url: "https://data-api.investoday.net/data/sse/preset",
        httpUrl: "https://data-api.investoday.net/data/mcp/preset",
        requiresApiKey: true,
        apiKeyPlaceholder: "请输入今日投资 API Key",
        category: "金融服务",
        apiKeyUrl: "https://data-api.investoday.net/user/login?redirect=/user/account"
    },
    {
        id: "stock_mcp",
        name: "腾讯股票数据",
        description: "实时股价查询、批量行情、持仓管理、观察列表，数据来源腾讯财经",
        icon: tencentFinanceIcon,
        type: "mcp" as const,
        transport: "stdio" as const,
        command: "npx",
        args: ["-y", "stock-mcp"],
        requiresApiKey: false,
        category: "行情数据"
    },
    {
        id: "tavily",
        name: "Tavily 搜索",
        description: "实时网络搜索、智能内容提取、网站爬取与结构化映射，专为 AI Agent 设计",
        icon: tavilyIcon,
        type: "mcp" as const,
        transport: "stdio" as const,
        command: "npx",
        args: ["-y", "tavily-mcp@latest"],
        requiresApiKey: true,
        apiKeyPlaceholder: "请输入 Tavily API Key",
        apiKeyLabel: "TAVILY_API_KEY",
        category: "搜索服务",
        apiKeyUrl: "https://www.tavily.com/"
    },
    {
        id: "firstdata",
        name: "FirstData 数据源",
        description: "全球权威一手数据源知识库，覆盖科研、政务、法律、金融等领域，支持智能检索与推荐",
        icon: firstdataIcon,
        type: "mcp" as const,
        transport: "http" as const,
        url: "https://firstdata.deepminer.com.cn/mcp",
        requiresApiKey: true,
        apiKeyPlaceholder: "请输入 FirstData API Key（Bearer Token）",
        category: "数据服务",
        apiKeyUrl: "https://github.com/MLT-OSS/FirstData"
    },
    {
        id: "skill_browser_takeover",
        name: "浏览器接管",
        description: "自动化浏览器操作，支持网页交互、表单填写等任务",
        icon: "🌐",
        type: "skill" as const,
        skillName: "browser_takeover",
        requiresApiKey: false,
        category: "智能技能"
    },
    {
        id: "skill_data_viz",
        name: "数据可视化",
        description: "将数据转化为图表，支持多种可视化方式",
        icon: "📊",
        type: "skill" as const,
        skillName: "data_viz",
        requiresApiKey: false,
        category: "智能技能"
    },
    {
        id: "skill_deep_research",
        name: "深度研究",
        description: "基于多源信息的深度调研与分析报告生成",
        icon: "🔬",
        type: "skill" as const,
        skillName: "deep_research",
        requiresApiKey: false,
        category: "智能技能"
    },
    {
        id: "skill_xhs_scraper",
        name: "小红书数据采集",
        description: "采集小红书笔记、评论等数据，支持关键词搜索与批量导出",
        icon: xiaohongshuIcon,
        type: "skill" as const,
        skillName: "xhs_scraper",
        requiresApiKey: false,
        category: "智能技能"
    },
    {
        id: "skill_mcp_builder",
        name: "MCP 服务器开发",
        description: "指导构建高质量 MCP 服务器，覆盖调研、实现、测试、评估四大阶段",
        icon: "🛠️",
        type: "skill" as const,
        skillName: "mcp_builder",
        requiresApiKey: false,
        category: "智能技能"
    },
    {
        id: "skill_skill_creator",
        name: "技能创建者",
        description: "指导设计和构建 Skill 技能包，包括工作流、工具集成和领域知识封装",
        icon: "✨",
        type: "skill" as const,
        skillName: "skill_creator",
        requiresApiKey: false,
        category: "智能技能"
    },
    {
        id: "skill_portfolio_manager",
        name: "个人持仓管理",
        description: "本地化管理用户的资金与持仓数据，根据对话意图智能判断何时询问与更新",
        icon: "💼",
        type: "skill" as const,
        skillName: "portfolio_manager",
        requiresApiKey: false,
        category: "金融服务"
    },
    {
        id: "feishu_bot",
        name: "飞书机器人",
        description: "连接飞书 Bot，通过手机飞书与 Agent 实时对话。需先在飞书开放平台创建应用并开启机器人能力",
        icon: feishuIcon,
        type: "channel" as const,
        requiresApiKey: true,
        apiKeyPlaceholder: "请输入 App Secret",
        category: "消息通道",
        apiKeyUrl: "https://open.feishu.cn"
    }
]

export function AgentSkillsModal({ open, onOpenChange }: AgentSkillsModalProps) {
    const { agents, currentAgentId, updateAgent } = useStore()
    const currentAgent = agents.find(a => a.id === currentAgentId)

    const [availableSkills, setAvailableSkills] = useState<SkillInfo[]>([])
    const [availableTools, setAvailableTools] = useState<ToolInfo[]>([])
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)

    const [mcpServers, setMcpServers] = useState<MCPServerConfig[]>([])
    const [showMcpForm, setShowMcpForm] = useState(false)
    const [editingMcp, setEditingMcp] = useState<MCPServerConfig | null>(null)
    const [mcpForm, setMcpForm] = useState<Partial<MCPServerConfig>>({
        name: "",
        transport: "stdio",
        command: "npx",
        args: [],
        env: {},
        url: "",
        api_key: "",
        headers: {},
        description: "",
        enabled: true
    })
    const [mcpArgsStr, setMcpArgsStr] = useState("")
    const [mcpEnvStr, setMcpEnvStr] = useState("")
    const [mcpExpanded, setMcpExpanded] = useState(true)
    const [saveMessage, setSaveMessage] = useState<string | null>(null)
    const [showMcpMarket, setShowMcpMarket] = useState(false)
    const [marketApiKey, setMarketApiKey] = useState<Record<string, string>>({})
    const [marketCategory, setMarketCategory] = useState<string>("全部")
    const [marketSearch, setMarketSearch] = useState("")

    useEffect(() => {
        if (open) {
            setLoading(true)
            Promise.all([fetchSkills(), fetchTools()])
                .then(([skills, tools]: [any, any]) => {
                    setAvailableSkills(Array.isArray(skills) ? skills : [])
                    setAvailableTools(Array.isArray(tools) ? tools : [])
                })
                .catch(console.error)
                .finally(() => setLoading(false))

            if (currentAgent) {
                const agentMcp = (currentAgent as any).mcp_servers || []
                setMcpServers(agentMcp)
            }
        }
    }, [open, currentAgent])

    useEffect(() => {
        if (editingMcp) {
            setMcpForm(editingMcp)
            setMcpArgsStr(editingMcp.args.join(" "))
            setMcpEnvStr(Object.entries(editingMcp.env || {}).map(([k, v]) => `${k}=${v}`).join("\n"))
        } else {
            setMcpForm({ name: "", transport: "stdio", command: "npx", args: [], env: {}, url: "", api_key: "", headers: {}, description: "", enabled: true })
            setMcpArgsStr("")
            setMcpEnvStr("")
        }
    }, [editingMcp, showMcpForm])

    if (!currentAgent) return null

    const agentTools: string[] = (currentAgent as any).tools || []
    const agentSkills: string[] = (currentAgent as any).skills || []
    const isMetaAgent = currentAgentId === "meta_agent"

    const toggleTool = async (toolName: string) => {
        if (isMetaAgent || saving || !currentAgentId) return
        setSaving(true)
        try {
            const newTools = agentTools.includes(toolName)
                ? agentTools.filter(t => t !== toolName)
                : [...agentTools, toolName]
            await updateAgent(currentAgentId, { tools: newTools })
        } catch (e) {
            console.error("更新工具失败:", e)
        } finally {
            setSaving(false)
        }
    }

    const toggleSkill = async (skillName: string) => {
        if (isMetaAgent || saving || !currentAgentId) return
        setSaving(true)
        try {
            const newSkills = agentSkills.includes(skillName)
                ? agentSkills.filter(s => s !== skillName)
                : [...agentSkills, skillName]
            await updateAgent(currentAgentId, { skills: newSkills })
        } catch (e) {
            console.error("更新技能失败:", e)
        } finally {
            setSaving(false)
        }
    }

    const parseEnvString = (str: string): Record<string, string> => {
        const env: Record<string, string> = {}
        str.split("\n").forEach(line => {
            const trimmed = line.trim()
            if (trimmed && trimmed.includes("=")) {
                const [key, ...valueParts] = trimmed.split("=")
                env[key.trim()] = valueParts.join("=").trim()
            }
        })
        return env
    }

    const handleSaveMcp = async () => {
        if (!mcpForm.name || !currentAgentId) return
        if (mcpForm.transport === "stdio" && !mcpForm.command) return
        if ((mcpForm.transport === "sse" || mcpForm.transport === "http") && !mcpForm.url) return

        const args = mcpArgsStr.split(" ").filter(a => a.trim())
        const env = parseEnvString(mcpEnvStr)

        const newMcp: MCPServerConfig = {
            id: editingMcp?.id || `mcp_${Date.now()}`,
            name: mcpForm.name,
            transport: mcpForm.transport || "stdio",
            command: mcpForm.command || "",
            args,
            env,
            url: mcpForm.url || "",
            api_key: mcpForm.api_key || "",
            headers: mcpForm.headers || {},
            description: mcpForm.description || "",
            enabled: mcpForm.enabled ?? true
        }

        let updatedServers: MCPServerConfig[]
        if (editingMcp) {
            updatedServers = mcpServers.map(s => s.id === editingMcp.id ? newMcp : s)
        } else {
            updatedServers = [...mcpServers, newMcp]
        }

        setMcpServers(updatedServers)
        setShowMcpForm(false)
        setEditingMcp(null)

        setSaving(true)
        try {
            await updateAgent(currentAgentId, { mcp_servers: updatedServers } as any)
            setSaveMessage("MCP 配置保存成功！")
            setTimeout(() => setSaveMessage(null), 2000)
        } catch (e) {
            console.error("保存 MCP 配置失败:", e)
            setSaveMessage("保存失败，请重试")
            setTimeout(() => setSaveMessage(null), 2000)
        } finally {
            setSaving(false)
        }
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const handleDeleteMcp = async (id: string) => {
        void handleDeleteMcp;
        if (!currentAgentId) return
        const updatedServers = mcpServers.filter(s => s.id !== id)
        setMcpServers(updatedServers)

        setSaving(true)
        try {
            await updateAgent(currentAgentId, { mcp_servers: updatedServers } as any)
            setSaveMessage("MCP 配置已删除")
            setTimeout(() => setSaveMessage(null), 2000)
        } catch (e) {
            console.error("删除 MCP 配置失败:", e)
            setSaveMessage("删除失败，请重试")
            setTimeout(() => setSaveMessage(null), 2000)
        } finally {
            setSaving(false)
        }
    }

    const handleAddFromMarket = async (item: typeof MCP_MARKET_ITEMS[0]) => {
        if (!currentAgentId) return

        setSaving(true)
        try {

            // Skill type: add skill name to agent skills
            if (item.type === "skill" && "skillName" in item) {
                const currentSkills: string[] = (currentAgent as any).skills || []
                const skillName = (item as any).skillName as string
                if (!currentSkills.includes(skillName)) {
                    const mergedSkills = [...currentSkills, skillName]
                    await updateAgent(currentAgentId, { skills: mergedSkills })
                }
                setSaveMessage(`${item.name} 已添加到 Agent！`)
                setTimeout(() => setSaveMessage(null), 2000)
                return
            }

            // Channel type (e.g. Feishu): register binding + add as MCP
            if (item.type === "channel") {
                const appId = marketApiKey[item.id + "_app_id"] || ""
                const appSecret = marketApiKey[item.id] || ""
                if (!appId || !appSecret) {
                    setSaveMessage("请填写 App ID 和 App Secret")
                    setTimeout(() => setSaveMessage(null), 3000)
                    return
                }
                const workspaceId = useStore.getState().currentWorkspaceId
                await registerFeishu(appId, appSecret, currentAgentId, workspaceId || "")

                // Also save as MCP-like config for UI display
                const newMcp: MCPServerConfig = {
                    id: `mcp_${item.id}_${Date.now()}`,
                    name: item.name,
                    transport: "sse",
                    command: "",
                    args: [],
                    env: {},
                    url: "",
                    api_key: appId,
                    headers: {},
                    description: item.description,
                    icon: item.icon,
                    enabled: true
                }
                const updatedServers = [...mcpServers, newMcp]
                setMcpServers(updatedServers)
                await updateAgent(currentAgentId, { mcp_servers: updatedServers } as any)

                setSaveMessage(`${item.name} 已连接！请在飞书开放平台配置事件订阅 URL`)
                setTimeout(() => setSaveMessage(null), 4000)
                setMarketApiKey(prev => { const next = { ...prev }; delete next[item.id]; delete next[item.id + "_app_id"]; return next })
                return
            }

            // MCP type: add MCP server config
            const apiKey = marketApiKey[item.id] || ""
            let url = (item as any).url || ""
            const headers: Record<string, string> = {}
            const env: Record<string, string> = {}

            // For stdio transport, pass API key as environment variable
            if ((item as any).transport === "stdio" && apiKey) {
                const envKey = (item as any).apiKeyLabel || "API_KEY"
                env[envKey] = apiKey
            }
            // For HTTP transport (streamable-http), put API key in Authorization header
            else if ((item as any).transport === "http" && apiKey) {
                headers["Authorization"] = `Bearer ${apiKey}`
            } else if (apiKey) {
                url = url.includes("?") ? `${url}&apiKey=${apiKey}` : `${url}?apiKey=${apiKey}`
            }

            const newMcp: MCPServerConfig = {
                id: `mcp_${item.id}_${Date.now()}`,
                name: item.name,
                transport: (item as any).transport || "sse",
                command: (item as any).command || "",
                args: (item as any).args || [],
                env: env,
                url: url,
                api_key: apiKey,
                headers: headers,
                description: item.description,
                icon: item.icon,
                enabled: true
            }

            const updatedServers = [...mcpServers, newMcp]
            setMcpServers(updatedServers)

            await updateAgent(currentAgentId, { mcp_servers: updatedServers } as any)
            setSaveMessage(`${item.name} 已添加到 MCP 配置！`)
            setTimeout(() => setSaveMessage(null), 2000)
            // Don't close market after adding — let user add more
            setMarketApiKey(prev => { const next = { ...prev }; delete next[item.id]; return next })
        } catch (e) {
            console.error("添加失败:", e)
            setSaveMessage("添加失败，请重试")
            setTimeout(() => setSaveMessage(null), 2000)
        } finally {
            setSaving(false)
        }
    }

    const handleToggleMcp = async (id: string) => {
        if (!currentAgentId) return
        const updatedServers = mcpServers.map(s =>
            s.id === id ? { ...s, enabled: !s.enabled } : s
        )
        setMcpServers(updatedServers)

        setSaving(true)
        try {
            await updateAgent(currentAgentId, { mcp_servers: updatedServers } as any)
        } catch (e) {
            console.error("切换 MCP 状态失败:", e)
        } finally {
            setSaving(false)
        }
    }

    const handleSelectPreset = (preset: typeof POPULAR_MCP_SERVERS[0]) => {
        const p = preset as any
        setMcpForm({
            name: preset.name,
            transport: preset.transport || "stdio",
            command: preset.command || "",
            args: preset.args || [],
            env: (preset.env || {}) as Record<string, string>,
            url: p.url || "",
            api_key: p.api_key || "",
            headers: {},
            description: preset.description,
            enabled: true
        })
        setMcpArgsStr((preset.args || []).join(" "))
        setMcpEnvStr(Object.entries(preset.env || {}).map(([k, v]) => `${k}=${v}`).join("\n"))
    }

    const toolsByGroup: Record<string, ToolInfo[]> = {}
    for (const t of availableTools) {
        const group = t.group || "其他"
        if (!toolsByGroup[group]) toolsByGroup[group] = []
        toolsByGroup[group].push(t)
    }

    // MCP Market: filter by category and search
    const filteredMarketItems = useMemo(() => {
        return MCP_MARKET_ITEMS.filter(item => {
            const matchCategory = marketCategory === "全部" || item.category === marketCategory
            const matchSearch = !marketSearch || item.name.toLowerCase().includes(marketSearch.toLowerCase()) || item.description.toLowerCase().includes(marketSearch.toLowerCase())
            return matchCategory && matchSearch
        })
    }, [marketCategory, marketSearch])

    // Check if an MCP market item is already added to this agent
    const isMarketItemAdded = (item: typeof MCP_MARKET_ITEMS[0]) => {
        if (item.type === "skill" && "skillName" in item) {
            return agentSkills.includes((item as any).skillName)
        }
        return mcpServers.some(s => s.id.includes(item.id))
    }

    // Handle dialog close — reset market state
    const handleOpenChange = (open: boolean) => {
        if (!open) {
            setShowMcpMarket(false)
            setMarketApiKey({})
            setMarketCategory("全部")
            setMarketSearch("")
        }
        onOpenChange(open)
    }

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-fit transition-all duration-300 ease-in-out p-0 border-0 bg-transparent shadow-none [&>button]:hidden">
                {saveMessage && (
                    <div className={`text-sm px-3 py-1.5 rounded-md absolute top-2 left-1/2 -translate-x-1/2 z-10 ${saveMessage.includes("成功") || saveMessage.includes("已添加") ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {saveMessage}
                    </div>
                )}

                <div className="flex gap-2 min-h-0 bg-[#F4F5F8] border border-[#E4E5EB] rounded-[12px] p-2 transition-all duration-300">
                    {/* ========== LEFT PANEL: Original Agent Capabilities ========== */}
                    <div className={`bg-white rounded-[10px] border border-[#E4E5EB] shadow-sm flex flex-col shrink-0 transition-all duration-300 ${showMcpMarket ? 'w-[450px]' : 'w-[552px]'}`}>
                        <div className="px-5 py-4 border-b border-[#F4F5F8] flex items-center justify-between shrink-0">
                            <div className="flex items-center gap-2 text-[16px] font-semibold text-[#111822]">
                                智能体工具
                            </div>
                        </div>
                        <ScrollArea className="flex-1 max-h-[70vh]">
                            <div className="p-5 space-y-6">
                                {/* 可配置工具与技能列表 (Linear Style) */}
                                <div className="space-y-0">
                                    {loading ? (
                                        <div className="text-xs text-[#8A8F98] animate-pulse py-4 text-center">加载中...</div>
                                    ) : (
                                        <>
                                            {Object.entries(toolsByGroup).map(([group, tools]) => {
                                                const filteredTools = tools.filter(t => !SYSTEM_DEFAULT_TOOLS.has(t.name) && (isMetaAgent || !META_AGENT_TOOLS.has(t.name)))
                                                if (filteredTools.length === 0) return null
                                                return filteredTools.map(t => {
                                                    const isEquipped = agentTools.includes(t.name)
                                                    return (
                                                        <div
                                                            key={t.name}
                                                            className="flex justify-between items-center py-3 px-1 border-b border-[#F4F5F8] group hover:bg-[#FAFBFC] transition-colors"
                                                        >
                                                            <div className="flex items-center gap-3">
                                                                <Wrench className="w-4 h-4 text-[#8A8F98] group-hover:text-[#5E6AD2] transition-colors" />
                                                                <span className="text-[13px] font-medium text-[#111822]">{t.label || t.name}</span>
                                                            </div>
                                                            <div className="flex items-center gap-3">
                                                                <span className="text-[12px] text-[#8A8F98] font-medium">{group}</span>
                                                                {!isMetaAgent && (
                                                                    <button
                                                                        onClick={() => toggleTool(t.name)}
                                                                        className={`w-9 h-5 rounded-full relative transition-colors duration-200 ${isEquipped ? 'bg-[#111822]' : 'bg-[#E4E5EB]'}`}
                                                                    >
                                                                        <div className={`absolute top-[2px] w-4 h-4 bg-white rounded-full shadow-sm transition-all duration-200 ${isEquipped ? 'right-[2px]' : 'left-[2px]'}`} />
                                                                    </button>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )
                                                })
                                            })}

                                            {/* 已装备的高级技能 */}
                                            {availableSkills.filter(s => agentSkills.includes(s.name)).map(s => {
                                                const isEquipped = agentSkills.includes(s.name)
                                                return (
                                                    <div
                                                        key={s.name}
                                                        className="flex justify-between items-center py-3 px-1 border-b border-[#F4F5F8] group hover:bg-[#FAFBFC] transition-colors"
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            <Zap className="w-4 h-4 text-[#8A8F98] group-hover:text-amber-500 transition-colors" />
                                                            <span className="text-[13px] font-medium text-[#111822]">{SKILL_LABELS[s.name] || s.name}</span>
                                                        </div>
                                                        <div className="flex items-center gap-3">
                                                            <span className="text-[12px] text-[#8A8F98] font-medium">高级技能</span>
                                                            {!isMetaAgent && (
                                                                <button
                                                                    onClick={() => toggleSkill(s.name)}
                                                                    className={`w-9 h-5 rounded-full relative transition-colors duration-200 ${isEquipped ? 'bg-[#111822]' : 'bg-[#E4E5EB]'}`}
                                                                >
                                                                    <div className={`absolute top-[2px] w-4 h-4 bg-white rounded-full shadow-sm transition-all duration-200 ${isEquipped ? 'right-[2px]' : 'left-[2px]'}`} />
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>
                                                )
                                            })}
                                        </>
                                    )}
                                </div>

                                {/* MCP 服务器配置 */}
                                <div className="space-y-3 pt-4 border-t">
                                    <div
                                        className="flex items-center justify-between cursor-pointer"
                                        onClick={() => setMcpExpanded(!mcpExpanded)}
                                    >
                                        <h3 className="text-sm font-semibold flex items-center gap-2 text-[#111822]">
                                            <Plug className="w-4 h-4 text-[#8A8F98]" /> MCP 服务器 ({mcpServers.length})
                                        </h3>
                                        {mcpExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                    </div>

                                    {mcpExpanded && (
                                        <div className="space-y-0">
                                            {/* 已配置的 MCP 列表 */}
                                            {mcpServers.length > 0 ? (
                                                <>
                                                    {mcpServers.map(server => (
                                                        <div
                                                            key={server.id}
                                                            className="flex justify-between items-center py-3 px-1 border-b border-[#F4F5F8] group hover:bg-[#FAFBFC] transition-colors"
                                                        >
                                                            <div className="flex items-center gap-3 min-w-0 flex-1">
                                                                {server.icon && typeof server.icon === 'string' && (server.icon.includes('/') || server.icon.includes('.')) ? (
                                                                    <img src={server.icon} alt={server.name} className="w-4 h-4 rounded-sm object-cover" />
                                                                ) : (
                                                                    <Plug className="w-4 h-4 text-[#8A8F98] group-hover:text-[#5E6AD2] transition-colors shrink-0" />
                                                                )}
                                                                <div className="min-w-0">
                                                                    <span className="text-[13px] font-medium text-[#111822]">{server.name}</span>
                                                                    <div className="text-[11px] text-[#8A8F98] truncate">
                                                                        {server.description || (server.transport === "stdio" ? "本地进程工具服务" : "远程 MCP 工具服务")}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-2 shrink-0">
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    className="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                    onClick={() => { setEditingMcp(server); setShowMcpForm(true); }}
                                                                    title="编辑"
                                                                >
                                                                    <Edit2 className="w-3.5 h-3.5 text-[#8A8F98]" />
                                                                </Button>
                                                                <button
                                                                    onClick={() => handleToggleMcp(server.id)}
                                                                    className={`w-9 h-5 rounded-full relative transition-colors duration-200 ${server.enabled ? 'bg-[#111822]' : 'bg-[#E4E5EB]'}`}
                                                                >
                                                                    <div className={`absolute top-[2px] w-4 h-4 bg-white rounded-full shadow-sm transition-all duration-200 ${server.enabled ? 'right-[2px]' : 'left-[2px]'}`} />
                                                                </button>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </>
                                            ) : (
                                                <div className="text-xs text-[#8A8F98] italic text-center py-3">
                                                    暂无 MCP 服务器配置
                                                </div>
                                            )}

                                            {/* 添加 MCP 按钮 */}
                                            {!isMetaAgent && !showMcpForm && (
                                                <div className="flex gap-2 pt-3">
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        className="flex-1 border-dashed border-[#E4E5EB] text-[#8A8F98] hover:bg-[#FAFBFC] hover:text-[#111822]"
                                                        onClick={() => setShowMcpForm(true)}
                                                    >
                                                        <Plus className="w-4 h-4 mr-1" /> 添加 MCP
                                                    </Button>
                                                    <Button
                                                        variant={showMcpMarket ? "default" : "outline"}
                                                        size="sm"
                                                        className={`flex-1 border-dashed ${showMcpMarket
                                                            ? 'bg-[#111822] text-white hover:bg-[#2a2f3a] border-[#111822]'
                                                            : 'border-[#E4E5EB] text-[#8A8F98] hover:bg-[#FAFBFC] hover:text-[#111822]'
                                                            }`}
                                                        onClick={() => setShowMcpMarket(!showMcpMarket)}
                                                    >
                                                        <Store className="w-4 h-4 mr-1" /> 工具市场
                                                    </Button>
                                                </div>
                                            )}



                                            {/* MCP 配置表单 */}
                                            {showMcpForm && (
                                                <div className="bg-white p-3 rounded-lg border space-y-3">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-sm font-medium">{editingMcp ? "编辑 MCP" : "添加 MCP"}</span>
                                                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => { setShowMcpForm(false); setEditingMcp(null); }}>
                                                            <X className="w-4 h-4" />
                                                        </Button>
                                                    </div>

                                                    {!editingMcp && (
                                                        <div className="space-y-1">
                                                            <Label className="text-xs">快速选择预设</Label>
                                                            <div className="flex flex-wrap gap-1">
                                                                {POPULAR_MCP_SERVERS.map(preset => (
                                                                    <Badge
                                                                        key={preset.name}
                                                                        variant="outline"
                                                                        className="cursor-pointer hover:bg-purple-100 text-xs"
                                                                        onClick={() => handleSelectPreset(preset)}
                                                                    >
                                                                        {preset.name}
                                                                    </Badge>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    <div className="grid grid-cols-2 gap-2">
                                                        <div className="space-y-1">
                                                            <Label className="text-xs">名称 *</Label>
                                                            <Input
                                                                value={mcpForm.name || ""}
                                                                onChange={e => setMcpForm({ ...mcpForm, name: e.target.value })}
                                                                placeholder="my-mcp-server"
                                                                className="h-8 text-sm"
                                                            />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <Label className="text-xs">传输类型 *</Label>
                                                            <select
                                                                value={mcpForm.transport || "stdio"}
                                                                onChange={e => setMcpForm({ ...mcpForm, transport: e.target.value as "stdio" | "sse" | "http" })}
                                                                className="w-full h-8 text-sm border rounded px-2"
                                                            >
                                                                <option value="stdio">stdio (本地进程)</option>
                                                                <option value="sse">SSE (远程推送)</option>
                                                                <option value="http">HTTP (远程请求)</option>
                                                            </select>
                                                        </div>
                                                    </div>

                                                    {mcpForm.transport === "stdio" && (
                                                        <>
                                                            <div className="grid grid-cols-2 gap-2">
                                                                <div className="space-y-1">
                                                                    <Label className="text-xs">命令 *</Label>
                                                                    <Input
                                                                        value={mcpForm.command || ""}
                                                                        onChange={e => setMcpForm({ ...mcpForm, command: e.target.value })}
                                                                        placeholder="npx"
                                                                        className="h-8 text-sm"
                                                                    />
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <Label className="text-xs">参数 (空格分隔)</Label>
                                                                    <Input
                                                                        value={mcpArgsStr}
                                                                        onChange={e => setMcpArgsStr(e.target.value)}
                                                                        placeholder="-y @anthropic-ai/mcp-server-filesystem"
                                                                        className="h-8 text-sm"
                                                                    />
                                                                </div>
                                                            </div>
                                                            <div className="space-y-1">
                                                                <Label className="text-xs">环境变量 (每行 KEY=VALUE)</Label>
                                                                <textarea
                                                                    value={mcpEnvStr}
                                                                    onChange={e => setMcpEnvStr(e.target.value)}
                                                                    placeholder="API_KEY=xxx&#10;ANOTHER_VAR=yyy"
                                                                    className="w-full h-16 text-xs border rounded p-2 resize-none"
                                                                />
                                                            </div>
                                                        </>
                                                    )}

                                                    {(mcpForm.transport === "sse" || mcpForm.transport === "http") && (
                                                        <>
                                                            <div className="space-y-1">
                                                                <Label className="text-xs">服务地址 *</Label>
                                                                <Input
                                                                    value={mcpForm.url || ""}
                                                                    onChange={e => setMcpForm({ ...mcpForm, url: e.target.value })}
                                                                    placeholder="https://mcp-service.example.com/sse"
                                                                    className="h-8 text-sm"
                                                                />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <Label className="text-xs">API Key</Label>
                                                                <Input
                                                                    type="password"
                                                                    value={mcpForm.api_key || ""}
                                                                    onChange={e => setMcpForm({ ...mcpForm, api_key: e.target.value })}
                                                                    placeholder="sk_xxx"
                                                                    className="h-8 text-sm"
                                                                />
                                                            </div>
                                                        </>
                                                    )}

                                                    <div className="space-y-1">
                                                        <Label className="text-xs">描述</Label>
                                                        <Input
                                                            value={mcpForm.description || ""}
                                                            onChange={e => setMcpForm({ ...mcpForm, description: e.target.value })}
                                                            placeholder="这个 MCP 服务器的用途..."
                                                            className="h-8 text-sm"
                                                        />
                                                    </div>

                                                    <div className="flex justify-end gap-2">
                                                        <Button variant="outline" size="sm" onClick={() => { setShowMcpForm(false); setEditingMcp(null); }}>
                                                            取消
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            onClick={handleSaveMcp}
                                                            disabled={!mcpForm.name || (mcpForm.transport === "stdio" && !mcpForm.command) || ((mcpForm.transport === "sse" || mcpForm.transport === "http") && !mcpForm.url)}
                                                        >
                                                            {editingMcp ? "保存" : "添加"}
                                                        </Button>
                                                    </div>
                                                </div>
                                            )}

                                        </div>
                                    )}
                                </div>



                            </div>
                        </ScrollArea>
                    </div>

                    {/* ========== RIGHT PANEL: MCP Market ========== */}
                    {showMcpMarket && (
                        <div className="w-[850px] bg-white rounded-[10px] border border-[#E4E5EB] shadow-sm flex flex-col max-h-[70vh] relative overflow-hidden flex-shrink border-l-0">
                            {/* Market Header */}
                            <div className="px-5 py-4 border-b border-[#F4F5F8] flex shrink-0">
                                <div className="flex items-center justify-between w-full">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[16px] font-semibold text-[#111822]">工具市场</span>
                                        <Badge className="bg-[#F4F5F8] text-[#8A8F98] text-[10px] px-1.5">{MCP_MARKET_ITEMS.length} 个服务</Badge>
                                    </div>
                                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:bg-[#F4F5F8]" onClick={() => { setShowMcpMarket(false); setMarketApiKey({}); setMarketCategory("全部"); setMarketSearch(""); }}>
                                        <X className="w-4 h-4" />
                                    </Button>
                                </div>
                            </div>

                            {/* Search + Category */}
                            <div className="px-5 py-3 border-b border-[#F4F5F8] space-y-2 shrink-0">
                                <div className="relative">
                                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#8A8F98]" />
                                    <Input
                                        placeholder="搜索服务..."
                                        value={marketSearch}
                                        onChange={e => setMarketSearch(e.target.value)}
                                        className="h-8 text-xs pl-8 bg-[#F4F5F8] border-0"
                                    />
                                </div>
                                <div className="flex gap-1">
                                    {MCP_MARKET_CATEGORIES.map(cat => (
                                        <Button
                                            key={cat}
                                            variant={marketCategory === cat ? "default" : "ghost"}
                                            size="sm"
                                            className={`h-7 text-xs px-3 ${marketCategory === cat
                                                ? 'bg-[#111822] text-white hover:bg-[#2a2f3a]'
                                                : 'text-[#8A8F98] hover:bg-[#F4F5F8]'
                                                }`}
                                            onClick={() => setMarketCategory(cat)}
                                        >
                                            {cat}
                                        </Button>
                                    ))}
                                </div>
                            </div>

                            {/* Market Items */}
                            <ScrollArea className="flex-1 min-h-0">
                                <div className="p-3 space-y-3">
                                    {filteredMarketItems.length === 0 ? (
                                        <div className="text-center py-8">
                                            <Search className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                                            <p className="text-sm text-muted-foreground">没有找到匹配的服务</p>
                                        </div>
                                    ) : (
                                        filteredMarketItems.map(item => {
                                            const alreadyAdded = isMarketItemAdded(item)
                                            return (
                                                <div
                                                    key={item.id}
                                                    className={`rounded-xl border p-4 space-y-3 transition-all ${alreadyAdded
                                                        ? 'bg-green-50/50 border-green-200'
                                                        : 'bg-white border-gray-200 hover:border-[#111822] hover:shadow-sm'
                                                        }`}
                                                >
                                                    {/* Card Header */}
                                                    <div className="flex items-start justify-between">
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-100 to-purple-100 flex items-center justify-center flex-shrink-0 overflow-hidden">
                                                                {typeof item.icon === 'string' && (item.icon.includes('/') || item.icon.includes('.')) ? (
                                                                    <img src={item.icon} alt={item.name} className="w-10 h-10 rounded-lg object-cover" />
                                                                ) : (
                                                                    <span className="text-xl">{item.icon}</span>
                                                                )}
                                                            </div>
                                                            <div>
                                                                <div className="text-sm font-semibold flex items-center gap-2">
                                                                    {item.name}
                                                                    {alreadyAdded && <Check className="w-3.5 h-3.5 text-green-600" />}
                                                                </div>
                                                                <div className="flex items-center gap-1.5 mt-0.5">
                                                                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">{item.category}</Badge>
                                                                    {item.type === "mcp" && "transport" in item && (
                                                                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-mono">{((item as any).transport || "").toUpperCase()}</Badge>
                                                                    )}

                                                                    {item.type === "skill" && (
                                                                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-mono text-amber-600 border-amber-300">技能</Badge>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        {"apiKeyUrl" in item && (item as any).apiKeyUrl && (
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                className="h-auto px-2 py-1 text-[10px] text-blue-500 hover:text-blue-700 hover:bg-blue-50 whitespace-nowrap"
                                                                onClick={() => window.open((item as any).apiKeyUrl, '_blank')}
                                                                title="去官网获取 API Key"
                                                            >
                                                                <ExternalLink className="w-3 h-3 mr-0.5" />去官网获取 API Key
                                                            </Button>
                                                        )}
                                                    </div>

                                                    {/* Description */}
                                                    <p className="text-xs text-gray-600 leading-relaxed">{item.description}</p>

                                                    {/* Service URL or Tool Names */}
                                                    {item.type === "mcp" && "url" in item && (
                                                        <div className="text-[11px] text-gray-400 font-mono truncate bg-gray-50 px-2 py-1 rounded">
                                                            {(item as any).url}
                                                        </div>
                                                    )}


                                                    {/* API Key + Add Button */}
                                                    {item.requiresApiKey && !alreadyAdded && (
                                                        <div className="space-y-1.5">
                                                            {item.type === "channel" && (
                                                                <Input
                                                                    type="text"
                                                                    placeholder="请输入 App ID"
                                                                    value={marketApiKey[item.id + "_app_id"] || ""}
                                                                    onChange={e => setMarketApiKey({ ...marketApiKey, [item.id + "_app_id"]: e.target.value })}
                                                                    className="h-8 text-xs"
                                                                />
                                                            )}
                                                            <Input
                                                                type="password"
                                                                placeholder={item.apiKeyPlaceholder}
                                                                value={marketApiKey[item.id] || ""}
                                                                onChange={e => setMarketApiKey({ ...marketApiKey, [item.id]: e.target.value })}
                                                                className="h-8 text-xs"
                                                            />
                                                        </div>
                                                    )}

                                                    {alreadyAdded ? (
                                                        <div className="flex items-center justify-center gap-1.5 text-xs text-green-600 font-medium py-1">
                                                            <Check className="w-3.5 h-3.5" />
                                                            已添加到当前 Agent
                                                        </div>
                                                    ) : (
                                                        <Button
                                                            size="sm"
                                                            className="w-full bg-[#111822] hover:bg-[#2a2f3a] h-8"
                                                            onClick={() => handleAddFromMarket(item)}
                                                            disabled={saving}
                                                        >
                                                            {saving ? <Loader2 className="w-3 h-3 mr-1.5 animate-spin" /> : <Plus className="w-3 h-3 mr-1.5" />}
                                                            一键添加到 Agent
                                                        </Button>
                                                    )}
                                                </div>
                                            )
                                        })
                                    )}

                                    {/* Footer hint */}
                                    <div className="text-center text-[11px] text-muted-foreground/60 pt-2 pb-1">
                                        更多优质 MCP 服务持续接入中...
                                    </div>
                                </div>
                            </ScrollArea>
                        </div>
                    )}
                </div> {/* end flex container */}

            </DialogContent>
        </Dialog>
    )
}
