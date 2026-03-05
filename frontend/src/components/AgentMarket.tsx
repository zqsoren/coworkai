import { useState, useEffect } from "react"
import { Search, Bot, Wrench, Download, Star, ChevronRight, Tags, Database, Cpu, Send, Loader2, Plug } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { useStore } from "@/store"
import { PublishAgentPanel } from "./PublishAgentPanel"
import { MarketAgentDetailPanel } from "./MarketAgentDetailPanel"
import { fetchMarketAgents } from "@/lib/api"
import type { MarketAgent } from "@/lib/api"

import { TOOL_LABELS, MCP_MARKET_ITEMS } from "./AgentSkillsModal"

const SKILL_LABELS: Record<string, string> = {
    ...TOOL_LABELS,
    "browser_takeover": "浏览器接管", "data_viz": "数据可视化",
    "deep_research": "深度研究", "xhs_scraper": "小红书数据采集",
    "mcp_builder": "MCP 服务器开发", "skill_creator": "技能创建者",
}


export function AgentMarket() {
    const { setPublishPanelOpen } = useStore()
    const [searchTerm, setSearchTerm] = useState("")
    const [activeTab, setActiveTab] = useState("agents")
    const [marketAgents, setMarketAgents] = useState<MarketAgent[]>([])
    const [isLoadingMarket, setIsLoadingMarket] = useState(false)
    const [detailAgent, setDetailAgent] = useState<MarketAgent | null>(null)
    const [isDetailOpen, setIsDetailOpen] = useState(false)

    // Fetch real market agents
    useEffect(() => {
        loadMarketAgents()
    }, [])

    const loadMarketAgents = async () => {
        setIsLoadingMarket(true)
        try {
            const agents = await fetchMarketAgents()
            setMarketAgents(agents)
        } catch (e) {
            console.error("Failed to fetch market agents:", e)
        } finally {
            setIsLoadingMarket(false)
        }
    }

    const filteredAgents = marketAgents.filter(agent =>
        agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (agent.description || "").toLowerCase().includes(searchTerm.toLowerCase())
    )

    const filteredTools = MCP_MARKET_ITEMS.filter(tool =>
        tool.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        tool.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        tool.category.toLowerCase().includes(searchTerm.toLowerCase())
    )

    const handleAgentClick = (agent: MarketAgent) => {
        setDetailAgent(agent)
        setIsDetailOpen(true)
    }

    return (
        <div className="flex flex-col h-full bg-[#f8f9fa] overflow-hidden">
            <PublishAgentPanel />
            <MarketAgentDetailPanel
                agent={detailAgent}
                isOpen={isDetailOpen}
                onClose={() => {
                    setIsDetailOpen(false)
                    // Refresh market data after close (in case import changed download count)
                    loadMarketAgents()
                }}
            />

            {/* Header */}
            <div className="px-8 py-6 bg-white border-b sticky top-0 z-10 shadow-sm flex flex-col gap-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 border-none m-0 shadow-none">智能体市场</h1>
                        <p className="text-gray-500 mt-2 text-sm">探索、发现并获取配置好知识库与技能的智能体和强大工具。</p>
                    </div>
                    <Button
                        onClick={() => setPublishPanelOpen(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-all gap-2 h-10 px-5 rounded-xl font-medium"
                    >
                        <Send className="w-4 h-4" />
                        发布我的智能体
                    </Button>
                </div>

                <div className="flex items-center justify-between">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-[400px]">
                        <TabsList className="grid w-full grid-cols-2 p-1 bg-gray-100 rounded-xl max-h-12 border-none">
                            <TabsTrigger value="agents" className="rounded-lg data-[state=active]:bg-white data-[state=active]:shadow-sm data-[state=active]:text-blue-600 border-none transition-all py-2">
                                <Bot className="w-4 h-4 mr-2" />
                                智能体发现
                            </TabsTrigger>
                            <TabsTrigger value="tools" className="rounded-lg data-[state=active]:bg-white data-[state=active]:shadow-sm data-[state=active]:text-emerald-600 border-none transition-all py-2">
                                <Wrench className="w-4 h-4 mr-2" />
                                工具与MCP
                            </TabsTrigger>
                        </TabsList>
                    </Tabs>

                    <div className="relative w-80">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                        <Input
                            placeholder={activeTab === 'agents' ? "搜索智能体名称或描述..." : "搜索工具、技能或分类..."}
                            className="pl-9 bg-gray-50 border-gray-200 rounded-xl focus-visible:ring-blue-500 shadow-none transition-shadow hover:bg-gray-100/50"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>
            </div>

            {/* Content Area */}
            <ScrollArea className="flex-1 px-8 py-8">

                <Tabs value={activeTab} className="w-full">
                    {/* Agents Tab */}
                    <TabsContent value="agents" className="m-0 border-none outline-none focus:outline-none focus-visible:ring-0 ring-0 focus-visible:outline-none">
                        {isLoadingMarket ? (
                            <div className="flex items-center justify-center py-20 text-gray-400 gap-2">
                                <Loader2 className="w-5 h-5 animate-spin" />
                                <span>加载市场数据...</span>
                            </div>
                        ) : filteredAgents.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 text-gray-400 gap-3">
                                <Bot className="w-12 h-12 text-gray-300" />
                                <span className="text-lg font-medium">暂无已发布的智能体</span>
                                <span className="text-sm">点击右上角「发布我的智能体」添加第一个！</span>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                                {filteredAgents.map(agent => (
                                    <div
                                        key={agent.id}
                                        onClick={() => handleAgentClick(agent)}
                                        className="group flex flex-col bg-white rounded-3xl border border-gray-100/80 shadow-[0_2px_12px_-4px_rgba(6,81,237,0.06)] hover:shadow-[0_12px_36px_-6px_rgba(6,81,237,0.12)] hover:-translate-y-1 transition-all duration-300 overflow-hidden cursor-pointer"
                                    >
                                        <div className="p-6 flex flex-col h-full gap-4">
                                            <div className="flex justify-between items-start">
                                                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100/50 group-hover:from-blue-600 group-hover:to-indigo-600 group-hover:text-white transition-all duration-300 shadow-sm">
                                                    <Bot className="w-6 h-6" />
                                                </div>
                                                <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-50/80 backdrop-blur-sm px-3 py-1.5 rounded-full border border-gray-100">
                                                    <Download className="w-3.5 h-3.5 text-gray-400" />
                                                    <span className="font-medium">{(agent.downloads || 0).toLocaleString()}</span>
                                                    <span className="mx-0.5 opacity-30 text-gray-300">|</span>
                                                    <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                                                    <span className="font-medium text-amber-600">{agent.rating || 5.0}</span>
                                                </div>
                                            </div>

                                            <div className="mt-1">
                                                <h3 className="text-[1.15rem] font-bold text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-1">{agent.name}</h3>
                                                <p className="text-[13px] text-gray-500 mt-2 line-clamp-2 leading-relaxed h-[38px]">{agent.description || agent.system_prompt?.slice(0, 80) || "暂无描述"}</p>
                                            </div>

                                            <div className="mt-3 flex-1 space-y-3.5 relative before:absolute before:inset-x-0 before:-top-3 before:h-px before:bg-gradient-to-r before:from-gray-100/0 before:via-gray-100/80 before:to-gray-100/0 pt-1">
                                                {/* Knowledge Base */}
                                                {agent.knowledge_base && agent.knowledge_base.length > 0 && (
                                                    <div className="space-y-2">
                                                        <div className="flex items-center text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                                                            <Database className="w-3.5 h-3.5 mr-1.5 opacity-70" />
                                                            内置知识库
                                                        </div>
                                                        <div className="flex flex-wrap gap-2">
                                                            {agent.knowledge_base.map((kb, idx) => (
                                                                <Badge key={idx} variant="secondary" className="bg-emerald-50/80 text-emerald-700 hover:bg-emerald-100 border border-emerald-100/50 truncate max-w-[180px] font-normal px-2.5 py-0.5 shadow-sm">
                                                                    {kb}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Skills */}
                                                <div className="space-y-2 pt-1">
                                                    <div className="flex items-center text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                                                        <Cpu className="w-3.5 h-3.5 mr-1.5 opacity-70" />
                                                        预置技能/工具
                                                    </div>
                                                    <div className="flex flex-wrap gap-1.5">
                                                        {[...(agent.tools || []), ...(agent.skills || [])].filter(s => s).map((skill, idx) => (
                                                            <Badge key={idx} variant="outline" className="bg-gray-50/50 border-gray-200/60 text-gray-600 font-normal px-2.5 py-0.5 truncate max-w-[150px] shadow-sm">
                                                                {SKILL_LABELS[skill] || skill}
                                                            </Badge>
                                                        ))}
                                                        {[...(agent.tools || []), ...(agent.skills || [])].filter(s => s).length === 0 && (
                                                            <span className="text-xs text-gray-400 italic">暂无</span>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* MCP Servers */}
                                                {(agent.mcp_servers && agent.mcp_servers.length > 0) && (
                                                    <div className="space-y-2 pt-1">
                                                        <div className="flex items-center text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                                                            <Plug className="w-3.5 h-3.5 mr-1.5 opacity-70" />
                                                            MCP 服务
                                                        </div>
                                                        <div className="flex flex-wrap gap-1.5">
                                                            {agent.mcp_servers.map((mcp: any, idx: number) => (
                                                                <Badge key={idx} variant="outline" className="bg-emerald-50/50 border-emerald-200/60 text-emerald-700 font-normal px-2.5 py-0.5 truncate max-w-[150px] shadow-sm">
                                                                    {mcp.name || mcp}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Action Bar */}
                                        <div className="px-6 py-4 bg-gray-50/70 border-t border-gray-100/60 flex justify-between items-center group-hover:bg-blue-50/40 transition-colors">
                                            <div className="flex items-center gap-1.5">
                                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
                                                <span className="text-xs text-gray-500 font-medium tracking-wide">可添加到工作区</span>
                                            </div>
                                            <Button variant="ghost" size="sm" className="text-blue-600 hover:text-blue-700 hover:bg-blue-100/60 font-semibold transition-colors h-8 px-3 rounded-lg">
                                                查看详情 <ChevronRight className="w-4 h-4 ml-0.5" />
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </TabsContent>

                    {/* Tools Tab */}
                    <TabsContent value="tools" className="m-0 border-none outline-none focus:outline-none focus-visible:ring-0 ring-0 focus-visible:outline-none">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                            {filteredTools.map(tool => (
                                <div key={tool.id} className="group p-5 bg-white rounded-3xl border border-gray-100/80 shadow-[0_2px_12px_-4px_rgba(6,81,237,0.06)] hover:shadow-[0_12px_36px_-6px_rgba(6,81,237,0.12)] hover:-translate-y-1 transition-all duration-300">
                                    <div className="flex items-start gap-4">
                                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-100/80 flex items-center justify-center shrink-0 overflow-hidden shadow-inner group-hover:shadow-[inset_0_2px_10px_-4px_rgba(0,0,0,0.1)] transition-shadow">
                                            {typeof tool.icon === 'string' && tool.icon.includes('/') ? (
                                                <img src={tool.icon} alt={tool.name} className="w-9 h-9 object-contain group-hover:scale-110 transition-transform duration-300" />
                                            ) : typeof tool.icon === 'string' ? (
                                                <div className="text-[28px] group-hover:scale-110 transition-transform duration-300">{tool.icon}</div>
                                            ) : null}
                                        </div>

                                        <div className="flex-1 min-w-0 pt-0.5">
                                            <div className="flex items-center justify-between gap-2 mb-1.5">
                                                <h3 className="text-base font-bold text-gray-900 group-hover:text-emerald-600 transition-colors truncate">{tool.name}</h3>
                                                <Badge variant="outline" className={cn(
                                                    "shrink-0 font-medium text-[10px] px-2 py-0.5 border-none shadow-sm",
                                                    tool.type === 'mcp' ? "bg-indigo-50/80 text-indigo-700 hover:bg-indigo-100" : "bg-orange-50/80 text-orange-700 hover:bg-orange-100"
                                                )}>
                                                    {tool.type === 'mcp' ? 'MCP Server' : 'Skill Module'}
                                                </Badge>
                                            </div>
                                            <p className="text-[13px] text-gray-500 line-clamp-2 leading-relaxed h-[40px]">{tool.description}</p>
                                        </div>
                                    </div>

                                    <div className="mt-5 pt-4 border-t border-gray-100/80 flex items-center justify-between">
                                        <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-50/80 px-2.5 py-1.5 rounded-lg border border-gray-100 shadow-sm">
                                            <Tags className="w-3.5 h-3.5 text-gray-400" />
                                            <span className="font-medium">{tool.category}</span>
                                        </div>
                                        <Button variant="outline" size="sm" className="h-8 px-4 rounded-xl text-xs font-semibold bg-white border-gray-200 hover:bg-gray-50 disabled:opacity-40 shadow-sm transition-colors" disabled>
                                            配置入库
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </TabsContent>
                </Tabs>

            </ScrollArea>
        </div>
    )
}
