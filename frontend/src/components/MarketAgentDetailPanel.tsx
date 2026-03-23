import { useState } from "react"
import { X, Bot, Database, Loader2, ChevronDown, Plus, Plug, Wrench } from "lucide-react"
import { useStore } from "@/store"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { importMarketAgent } from "@/lib/api"
import type { MarketAgent } from "@/lib/api"
import { getAvatarImage } from "./RightPanel"
import yingmiIcon from "@/assets/icons/yingmi.png"
import tianyanchaIcon from "@/assets/icons/tianyancha.png"
import investodayIcon from "@/assets/icons/investoday.png"
import tencentFinanceIcon from "@/assets/icons/tencent_finance.png"
import firstdataIcon from "@/assets/icons/firstdata.png"

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
    "close_browser": "关闭浏览器", "create_new_agent": "创建Agent",
    "search_knowledge_base": "知识库检索", "get_realtime_stock_data": "实时股价查询",
    "search_stock_by_name": "股票代码搜索",
}

const SKILL_LABELS: Record<string, string> = {
    "browser_takeover": "浏览器接管", "data_viz": "数据可视化",
    "deep_research": "深度研究", "xhs_scraper": "小红书数据采集",
    "mcp_builder": "MCP 服务器开发", "skill_creator": "技能创建者",
}

interface MarketAgentDetailPanelProps {
    agent: MarketAgent | null
    isOpen: boolean
    onClose: () => void
}

export function MarketAgentDetailPanel({ agent, isOpen, onClose }: MarketAgentDetailPanelProps) {
    const { workspaces, setCurrentWorkspaceId } = useStore()
    const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("")
    const [isImporting, setIsImporting] = useState(false)
    const [importSuccess, setImportSuccess] = useState(false)
    const [showDropdown, setShowDropdown] = useState(false)

    const selectedWorkspace = workspaces.find(w => w.id === selectedWorkspaceId)

    const handleImport = async () => {
        if (!agent || !selectedWorkspaceId) return
        setIsImporting(true)
        try {
            await importMarketAgent(agent.id, selectedWorkspaceId)
            setImportSuccess(true)
            // Refresh the workspace agents
            setCurrentWorkspaceId(selectedWorkspaceId)
            setTimeout(() => {
                setImportSuccess(false)
                onClose()
            }, 2000)
        } catch (e) {
            console.error("Import failed:", e)
        } finally {
            setIsImporting(false)
        }
    }

    const allSkills = [...(agent?.tools || []), ...(agent?.skills || [])].filter(s => s)

    return (
        <>
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity"
                    onClick={onClose}
                />
            )}

            <div className={cn(
                "fixed top-0 right-0 h-full w-[40vw] bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col",
                isOpen ? "translate-x-0" : "translate-x-full"
            )}>
                {/* Header */}
                <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-white/80 backdrop-blur-md">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl overflow-hidden shadow-md">
                            {(agent as any)?.avatar ? (
                                <img src={getAvatarImage((agent as any).avatar)} alt={agent?.name} className="w-full h-full object-cover" />
                            ) : (
                                <div className="w-full h-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center">
                                    <Bot className="w-5 h-5" />
                                </div>
                            )}
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">{agent?.name || "智能体详情"}</h2>
                            <p className="text-xs text-gray-500 mt-0.5">查看配置详情并一键添加到工作区</p>
                        </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-gray-100">
                        <X className="w-5 h-5 text-gray-500" />
                    </Button>
                </div>

                {agent && (
                    <>
                        {/* Content */}
                        <ScrollArea className="flex-1 p-6">
                            <div className="space-y-6">
                                {/* Description */}
                                {agent.description && (
                                    <div className="text-sm text-gray-600 leading-relaxed bg-blue-50/50 rounded-xl p-4 border border-blue-100/50">
                                        {agent.description}
                                    </div>
                                )}

                                {/* Stats */}
                                <div className="flex items-center gap-4 text-sm">
                                    <Badge variant="secondary" className="bg-gray-100 text-gray-600 font-medium border border-gray-200 gap-1">
                                        📥 {agent.downloads} 次导入
                                    </Badge>
                                    <Badge variant="secondary" className="bg-amber-50 text-amber-700 font-medium border border-amber-200 gap-1">
                                        ⭐ {agent.rating}
                                    </Badge>
                                </div>


                                {/* Knowledge Base */}
                                <div className="space-y-2">
                                    <h4 className="flex items-center text-sm font-semibold text-gray-700">
                                        <Database className="w-4 h-4 mr-2 text-gray-400" />
                                        关联知识库
                                    </h4>
                                    <div className="bg-gray-50 rounded-xl p-4 border border-gray-100/80">
                                        <div className="flex flex-wrap gap-2">
                                            {(agent.knowledge_base && agent.knowledge_base.length > 0) ? (
                                                agent.knowledge_base.map((kb, idx) => (
                                                    <Badge key={idx} variant="outline" className="bg-white px-3 py-1 text-sm font-normal shadow-sm border-gray-200 text-emerald-600">
                                                        📄 {kb}
                                                    </Badge>
                                                ))
                                            ) : (
                                                <span className="text-sm text-gray-400 italic">暂无关联知识库</span>
                                            )}
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
                                        {(agent.mcp_servers && agent.mcp_servers.length > 0) ? (
                                            agent.mcp_servers.map((mcp: any, idx: number) => (
                                                <div key={idx} className="flex items-center gap-3 px-4 py-2.5">
                                                    {(() => {
                                                        const iconSrc = MCP_ICON_MAP[mcp.name] || MCP_ICON_MAP[mcp.id?.replace(/^mcp_/, '').replace(/_\d+$/, '')] || null
                                                        if (iconSrc) return <img src={iconSrc} alt={mcp.name} className="w-5 h-5 rounded-sm object-cover shrink-0" />
                                                        return <Plug className="w-4 h-4 text-emerald-500 shrink-0" />
                                                    })()}
                                                    <div className="min-w-0">
                                                        <span className="text-sm text-gray-700 font-medium">{mcp.name || mcp}</span>
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

                        {/* Footer: Import Action */}
                        <div className="p-6 border-t border-gray-100 bg-gray-50/30">
                            <div className="flex items-center gap-3">
                                {/* Workspace Selector */}
                                <div className="relative w-1/3">
                                    <button
                                        onClick={() => setShowDropdown(!showDropdown)}
                                        className="w-full h-12 px-4 rounded-xl bg-white border border-gray-200 text-left text-sm flex items-center justify-between hover:border-blue-300 transition-colors shadow-sm"
                                    >
                                        <span className={selectedWorkspace ? "text-gray-800 font-medium" : "text-gray-400"}>
                                            {selectedWorkspace ? selectedWorkspace.name : "选择目标工作区..."}
                                        </span>
                                        <ChevronDown className={cn("w-4 h-4 text-gray-400 transition-transform", showDropdown && "rotate-180")} />
                                    </button>
                                    {showDropdown && (
                                        <div className="absolute bottom-full left-0 w-full mb-2 bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden z-10">
                                            <ScrollArea className="max-h-[200px]">
                                                {workspaces.map(ws => (
                                                    <button
                                                        key={ws.id}
                                                        onClick={() => {
                                                            setSelectedWorkspaceId(ws.id)
                                                            setShowDropdown(false)
                                                        }}
                                                        className={cn(
                                                            "w-full text-left px-4 py-3 text-sm hover:bg-blue-50 transition-colors border-b border-gray-50 last:border-0",
                                                            selectedWorkspaceId === ws.id ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700"
                                                        )}
                                                    >
                                                        {ws.name}
                                                    </button>
                                                ))}
                                            </ScrollArea>
                                        </div>
                                    )}
                                </div>

                                {/* Import Button */}
                                <Button
                                    className={cn(
                                        "h-12 px-6 text-base font-bold transition-all shadow-md flex-1",
                                        importSuccess ? "bg-emerald-500 hover:bg-emerald-600" : "bg-blue-600 hover:bg-blue-700"
                                    )}
                                    onClick={handleImport}
                                    disabled={isImporting || importSuccess || !selectedWorkspaceId}
                                >
                                    {importSuccess ? (
                                        <>✅ 添加成功！</>
                                    ) : isImporting ? (
                                        <><Loader2 className="w-5 h-5 mr-2 animate-spin" />导入中...</>
                                    ) : (
                                        <>
                                            <Plus className="w-5 h-5 mr-1" />
                                            一键添加
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </>
    )
}
