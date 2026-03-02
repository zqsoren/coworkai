import { useState, useEffect } from "react"
import { X, Send, Bot, Database, Command, Loader2, Folder, Plug, Wrench } from "lucide-react"
import { useStore } from "@/store"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { fetchAgents, publishAgentToMarket } from "@/lib/api"
import type { Agent } from "@/lib/api"
import yingmiIcon from "@/assets/icons/yingmi.png"
import tianyanchaIcon from "@/assets/icons/tianyancha.png"
import investodayIcon from "@/assets/icons/investoday.png"
import tencentFinanceIcon from "@/assets/icons/tencent_finance.png"
import firstdataIcon from "@/assets/icons/firstdata.png"

// MCP 名称 → 本地图标映射
const MCP_ICON_MAP: Record<string, string> = {
    "天眼查": tianyanchaIcon,
    "盈米基金": yingmiIcon,
    "今日投资": investodayIcon,
    "腾讯股票数据": tencentFinanceIcon,
    "腾讯财报研报": tencentFinanceIcon,
    "FirstData 数据源": firstdataIcon,
    "firstdata": firstdataIcon,
    "tianyancha": tianyanchaIcon,
    "yingmi": yingmiIcon,
    "investoday": investodayIcon,
    "tencent_finance": tencentFinanceIcon,
    "stock_mcp": tencentFinanceIcon,
}

const TOOL_LABELS: Record<string, string> = {
    "read_file": "读取文件", "write_file": "写入文件", "list_directory": "列出目录",
    "move_file": "移动文件", "get_file_diff": "文件对比", "google_search": "搜索引擎",
    "fetch_url_content": "抓取网页", "python_repl": "Python 执行器",
    "get_current_time": "获取当前时间", "take_screenshot": "屏幕截图",
    "open_browser": "打开浏览器", "get_page_text": "获取页面文本",
    "page_screenshot": "页面截图", "scroll_page": "滚动页面",
    "check_login_status": "检测登录状态", "wait_for_login": "等待扫码登录",
    "close_browser": "关闭浏览器", "create_new_agent": "创建新Agent",
    "list_available_agents": "列出所有Agent", "read_any_file": "读取任意文件",
    "search_files_by_keyword": "关键词搜索文件", "suggest_delegation_to_agent": "委派任务给Agent",
    "search_knowledge_base": "知识库检索", "get_realtime_stock_data": "实时股价查询",
    "search_stock_by_name": "股票代码搜索",
}

const SKILL_LABELS: Record<string, string> = {
    "browser_takeover": "浏览器接管", "data_viz": "数据可视化",
    "deep_research": "深度研究", "xhs_scraper": "小红书数据采集",
    "mcp_builder": "MCP 服务器开发", "skill_creator": "技能创建者",
}

interface AgentWithWorkspace extends Agent {
    workspaceName: string;
}

export function PublishAgentPanel() {
    const { isPublishPanelOpen, setPublishPanelOpen, workspaces } = useStore()
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
    const [isPublishing, setIsPublishing] = useState(false)
    const [publishSuccess, setPublishSuccess] = useState(false)
    const [allAgents, setAllAgents] = useState<AgentWithWorkspace[]>([])
    const [isLoadingAgents, setIsLoadingAgents] = useState(false)
    const [editedPrompt, setEditedPrompt] = useState("")

    // Fetch agents from ALL workspaces when panel opens
    useEffect(() => {
        if (!isPublishPanelOpen) return
        setIsLoadingAgents(true)
        setSelectedAgentId(null)
        setEditedPrompt("")
        setPublishSuccess(false)

        const loadAll = async () => {
            try {
                const results: AgentWithWorkspace[] = []
                for (const ws of workspaces) {
                    const agents = await fetchAgents(ws.id)
                    for (const agent of agents) {
                        if (agent.id === 'meta_agent') continue
                        results.push({ ...agent, workspaceName: ws.name })
                    }
                }
                setAllAgents(results)
            } catch (e) {
                console.error("Failed to load agents for publish panel:", e)
            } finally {
                setIsLoadingAgents(false)
            }
        }
        loadAll()
    }, [isPublishPanelOpen, workspaces])

    const selectedAgent = allAgents.find(a => a.id === selectedAgentId) || (allAgents.length > 0 ? allAgents[0] : null)

    // Sync editedPrompt when selected agent changes
    useEffect(() => {
        if (selectedAgent) {
            setEditedPrompt(selectedAgent.system_prompt || "")
        }
    }, [selectedAgent?.id])

    const handlePublish = async () => {
        if (!selectedAgent) return
        setIsPublishing(true)
        try {
            await publishAgentToMarket({
                name: selectedAgent.name,
                system_prompt: editedPrompt, // Use the EDITED prompt, not the original
                description: selectedAgent.system_prompt?.slice(0, 100) || "",
                tools: selectedAgent.tools || [],
                skills: selectedAgent.skills || [],
                mcp_servers: (selectedAgent as any).mcp_servers || [],
                knowledge_base: [],
            })
            setPublishSuccess(true)
            setTimeout(() => {
                setPublishSuccess(false)
                setPublishPanelOpen(false)
            }, 2000)
        } catch (e) {
            console.error("Publish failed:", e)
        } finally {
            setIsPublishing(false)
        }
    }

    const allSkills = [...(selectedAgent?.tools || []), ...(selectedAgent?.skills || [])].filter(s => s)

    // Group agents by workspace
    const agentsByWorkspace: Record<string, AgentWithWorkspace[]> = {}
    for (const agent of allAgents) {
        if (!agentsByWorkspace[agent.workspaceName]) {
            agentsByWorkspace[agent.workspaceName] = []
        }
        agentsByWorkspace[agent.workspaceName].push(agent)
    }

    return (
        <>
            {isPublishPanelOpen && (
                <div
                    className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity"
                    onClick={() => setPublishPanelOpen(false)}
                />
            )}

            <div className={cn(
                "fixed top-0 right-0 h-full w-[40vw] bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col",
                isPublishPanelOpen ? "translate-x-0" : "translate-x-full"
            )}>
                <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-white/80 backdrop-blur-md">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900">发布我的智能体</h2>
                        <p className="text-xs text-gray-500 mt-1">选择智能体并编辑提示词后发布至市场（不影响原 Agent）</p>
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => setPublishPanelOpen(false)} className="rounded-full hover:bg-gray-100">
                        <X className="w-5 h-5 text-gray-500" />
                    </Button>
                </div>

                <div className="flex flex-1 overflow-hidden">
                    {/* Left: Agent List */}
                    <div className="w-1/3 border-r border-gray-100 bg-gray-50/50 flex flex-col">
                        <div className="p-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            全部智能体 <span className="ml-1 text-gray-400">({allAgents.length})</span>
                        </div>
                        <ScrollArea className="flex-1 px-3 pb-4">
                            {isLoadingAgents ? (
                                <div className="flex items-center justify-center py-10 text-gray-400 gap-2 text-sm">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    加载中...
                                </div>
                            ) : allAgents.length === 0 ? (
                                <div className="text-sm text-gray-400 text-center py-10">暂无可用智能体</div>
                            ) : (
                                <div className="space-y-4">
                                    {Object.entries(agentsByWorkspace).map(([wsName, agents]) => (
                                        <div key={wsName}>
                                            <div className="flex items-center gap-1.5 px-2 py-1 mb-1.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                                                <Folder className="w-3 h-3" />
                                                {wsName}
                                            </div>
                                            <div className="space-y-1.5">
                                                {agents.map(agent => (
                                                    <button
                                                        key={agent.id}
                                                        onClick={() => setSelectedAgentId(agent.id)}
                                                        className={cn(
                                                            "w-full text-left px-4 py-3 rounded-xl transition-all duration-200 border",
                                                            (selectedAgent && selectedAgent.id === agent.id)
                                                                ? "bg-white border-blue-200 shadow-[0_2px_10px_-4px_rgba(59,130,246,0.3)]"
                                                                : "bg-transparent border-transparent hover:bg-gray-100/80"
                                                        )}
                                                    >
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <Bot className={cn("w-4 h-4", (selectedAgent && selectedAgent.id === agent.id) ? "text-blue-500" : "text-gray-400")} />
                                                            <span className={cn("text-sm font-semibold truncate", (selectedAgent && selectedAgent.id === agent.id) ? "text-blue-700" : "text-gray-700")}>
                                                                {agent.name}
                                                            </span>
                                                        </div>
                                                        <div className="text-xs text-gray-500 line-clamp-1 pl-6">
                                                            {agent.model_name || '未配置模型'}
                                                        </div>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </ScrollArea>
                    </div>

                    {/* Right: Agent Details */}
                    <div className="flex-1 flex flex-col bg-white">
                        {selectedAgent ? (
                            <ScrollArea className="flex-1 p-6">
                                <div className="space-y-6">
                                    <div>
                                        <h3 className="text-2xl font-bold text-gray-900">{selectedAgent.name}</h3>
                                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                                            <Badge variant="secondary" className="bg-blue-50 text-blue-700 font-medium border border-blue-100">
                                                模型: {selectedAgent.model_name || '暂无'}
                                            </Badge>
                                            <Badge variant="secondary" className="bg-gray-100 text-gray-600 font-medium border border-gray-200">
                                                <Folder className="w-3 h-3 mr-1" />
                                                工作区: {selectedAgent.workspaceName}
                                            </Badge>
                                        </div>
                                    </div>

                                    {/* Editable Prompt */}
                                    <div className="space-y-2">
                                        <h4 className="flex items-center text-sm font-semibold text-gray-700">
                                            <Command className="w-4 h-4 mr-2 text-gray-400" />
                                            系统提示词 / 角色设定
                                            <span className="ml-2 text-xs text-blue-500 font-normal">（可编辑，不影响原 Agent）</span>
                                        </h4>
                                        <Textarea
                                            className="min-h-[160px] bg-gray-50 rounded-xl border border-gray-200 text-sm text-gray-700 leading-relaxed resize-y focus-visible:ring-blue-500"
                                            value={editedPrompt}
                                            onChange={(e) => setEditedPrompt(e.target.value)}
                                            placeholder="输入系统提示词..."
                                        />
                                    </div>

                                    {/* Knowledge Base */}
                                    <div className="space-y-2">
                                        <h4 className="flex items-center text-sm font-semibold text-gray-700">
                                            <Database className="w-4 h-4 mr-2 text-gray-400" />
                                            关联知识库
                                        </h4>
                                        <div className="bg-gray-50 rounded-xl p-4 border border-gray-100/80">
                                            <div className="flex flex-wrap gap-2">
                                                <Badge variant="outline" className="bg-white px-3 py-1 text-sm font-normal shadow-sm border-gray-200">
                                                    📄 default_rag_doc.pdf
                                                </Badge>
                                                <Badge variant="outline" className="bg-white px-3 py-1 text-sm font-normal shadow-sm border-gray-200 text-gray-400">
                                                    + 待上传
                                                </Badge>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Tools & Skills */}
                                    <div className="space-y-2">
                                        <h4 className="flex items-center text-sm font-semibold text-gray-700">
                                            <Wrench className="w-4 h-4 mr-2 text-gray-400" />
                                            搭载工具与技能
                                        </h4>
                                        <div className="bg-gray-50 rounded-xl border border-gray-100/80 divide-y divide-gray-100">
                                            {allSkills.length > 0 ? (
                                                allSkills.map((skill, idx) => (
                                                    <div key={idx} className="flex items-center gap-3 px-4 py-2.5">
                                                        <Wrench className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                                                        <span className="text-sm text-gray-700">{TOOL_LABELS[skill] || SKILL_LABELS[skill] || skill}</span>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="px-4 py-3 text-sm text-gray-400 italic">未配置任何工具/技能</div>
                                            )}
                                        </div>
                                    </div>

                                    {/* MCP Servers */}
                                    <div className="space-y-2">
                                        <h4 className="flex items-center text-sm font-semibold text-gray-700">
                                            <Plug className="w-4 h-4 mr-2 text-gray-400" />
                                            MCP 服务
                                        </h4>
                                        <div className="bg-gray-50 rounded-xl border border-gray-100/80 divide-y divide-gray-100">
                                            {((selectedAgent as any)?.mcp_servers || []).length > 0 ? (
                                                ((selectedAgent as any).mcp_servers as any[]).map((mcp: any, idx: number) => (
                                                    <div key={idx} className="flex items-center gap-3 px-4 py-2.5">
                                                        {(() => {
                                                            const iconSrc = MCP_ICON_MAP[mcp.name] || MCP_ICON_MAP[mcp.id?.replace(/^mcp_/, '').replace(/_\d+$/, '')] || null
                                                            if (iconSrc) return <img src={iconSrc} alt={mcp.name} className="w-5 h-5 rounded-sm object-cover shrink-0" />
                                                            return <Plug className="w-4 h-4 text-emerald-500 shrink-0" />
                                                        })()}
                                                        <div className="min-w-0">
                                                            <span className="text-sm text-gray-700 font-medium">{mcp.name}</span>
                                                            {mcp.description && (
                                                                <span className="text-xs text-gray-400 ml-2">{mcp.description}</span>
                                                            )}
                                                        </div>
                                                        <Badge variant="outline" className="ml-auto shrink-0 text-[10px] px-1.5 py-0 border-gray-200 text-gray-400">
                                                            {mcp.transport || 'sse'}
                                                        </Badge>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="px-4 py-3 text-sm text-gray-400 italic">未配置任何 MCP 服务</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </ScrollArea>
                        ) : (
                            <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
                                {isLoadingAgents ? "加载中..." : "请在左侧选择要发布的智能体"}
                            </div>
                        )}

                        <div className="p-6 border-t border-gray-100 bg-gray-50/30">
                            <Button
                                className={cn(
                                    "w-full h-12 text-base font-bold transition-all shadow-md",
                                    publishSuccess ? "bg-emerald-500 hover:bg-emerald-600" : "bg-blue-600 hover:bg-blue-700"
                                )}
                                onClick={handlePublish}
                                disabled={isPublishing || publishSuccess || !selectedAgent || allAgents.length === 0}
                            >
                                {publishSuccess ? (
                                    <>✅ 发布成功！</>
                                ) : isPublishing ? (
                                    <><Loader2 className="w-5 h-5 mr-2 animate-spin" />发布中...</>
                                ) : (
                                    <>
                                        <Send className="w-5 h-5 mr-2" />
                                        一键发布至市场
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </>
    )
}
