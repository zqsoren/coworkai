import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Wrench, Zap } from "lucide-react"
import { useStore } from "@/store"
import { useEffect, useState } from "react"
import { fetchSkills, fetchTools } from "@/lib/api"

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

// 工具中文名映射（用于 Agent 已装备列表的展示）
const TOOL_LABELS: Record<string, string> = {
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
}

// Skill 中文名映射
const SKILL_LABELS: Record<string, string> = {
    "browser_takeover": "浏览器接管",
    "data_viz": "数据可视化",
    "deep_research": "深度研究",
    "xhs_scraper": "小红书数据采集",
}

export function AgentSkillsModal({ open, onOpenChange }: AgentSkillsModalProps) {
    const { agents, currentAgentId } = useStore()
    const currentAgent = agents.find(a => a.id === currentAgentId)

    const [availableSkills, setAvailableSkills] = useState<SkillInfo[]>([])
    const [availableTools, setAvailableTools] = useState<ToolInfo[]>([])
    const [loading, setLoading] = useState(false)

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
        }
    }, [open])

    if (!currentAgent) return null

    const agentTools: string[] = (currentAgent as any).tools || []
    const agentSkills: string[] = (currentAgent as any).skills || []

    // 按 group 分组工具
    const toolsByGroup: Record<string, ToolInfo[]> = {}
    for (const t of availableTools) {
        const group = t.group || "其他"
        if (!toolsByGroup[group]) toolsByGroup[group] = []
        toolsByGroup[group].push(t)
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[550px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Zap className="w-5 h-5 text-amber-500" />
                        Agent 能力面板 ({currentAgent.name})
                    </DialogTitle>
                    <DialogDescription>
                        当前 Agent 已装备的工具和技能，以及系统所有可用能力。
                    </DialogDescription>
                </DialogHeader>

                <ScrollArea className="max-h-[60vh] pr-4">
                    <div className="space-y-6">

                        {/* 该 Agent 拥有的能力 */}
                        <div className="space-y-3">
                            <h3 className="text-sm font-semibold flex items-center gap-2 text-primary">
                                <Zap className="w-4 h-4" /> 已装备能力
                            </h3>
                            <div className="bg-muted/30 p-3 rounded-lg border space-y-4">
                                <div>
                                    <div className="text-xs text-muted-foreground mb-2">已装备工具</div>
                                    <div className="flex flex-wrap gap-2">
                                        {agentTools.length > 0 ? agentTools.map((t: string) => (
                                            <Badge key={t} variant="secondary" className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                                                {TOOL_LABELS[t] || t}
                                            </Badge>
                                        )) : <span className="text-xs text-muted-foreground italic">暂无工具</span>}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-xs text-muted-foreground mb-2">已装备技能</div>
                                    <div className="flex flex-wrap gap-2">
                                        {agentSkills.length > 0 ? agentSkills.map((s: string) => (
                                            <Badge key={s} variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100">
                                                {SKILL_LABELS[s] || s}
                                            </Badge>
                                        )) : <span className="text-xs text-muted-foreground italic">暂无技能</span>}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 系统可用能力大盘 */}
                        <div className="space-y-3 pt-4 border-t">
                            <h3 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
                                <Wrench className="w-4 h-4" /> 系统总可用大盘
                            </h3>

                            {loading ? (
                                <div className="text-xs text-muted-foreground animate-pulse">加载中...</div>
                            ) : (
                                <div className="space-y-4">
                                    {/* 工具按分组显示 */}
                                    {Object.entries(toolsByGroup).map(([group, tools]) => (
                                        <div key={group}>
                                            <div className="text-xs text-muted-foreground mb-2">{group}</div>
                                            <div className="flex flex-wrap gap-1.5">
                                                {tools.map(t => (
                                                    <Badge
                                                        key={t.name}
                                                        variant="outline"
                                                        className={`text-xs ${agentTools.includes(t.name) ? "border-blue-500 text-blue-600 bg-blue-50" : ""}`}
                                                        title={t.description}
                                                    >
                                                        {t.label || t.name}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    ))}

                                    {/* 技能 */}
                                    <div>
                                        <div className="text-xs text-muted-foreground mb-2">高级技能</div>
                                        <div className="flex flex-wrap gap-1.5">
                                            {availableSkills.map(s => (
                                                <Badge
                                                    key={s.name}
                                                    variant="outline"
                                                    className={`text-xs ${agentSkills.includes(s.name) ? "border-amber-500 text-amber-600 bg-amber-50" : ""}`}
                                                    title={s.description}
                                                >
                                                    {SKILL_LABELS[s.name] || s.name}
                                                </Badge>
                                            ))}
                                            {availableSkills.length === 0 && (
                                                <span className="text-xs text-muted-foreground italic">暂无可用技能</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                    </div>
                </ScrollArea>
            </DialogContent>
        </Dialog>
    )
}

