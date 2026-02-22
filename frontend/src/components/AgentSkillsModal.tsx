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

export function AgentSkillsModal({ open, onOpenChange }: AgentSkillsModalProps) {
    const { agents, currentAgentId } = useStore()
    const currentAgent = agents.find(a => a.id === currentAgentId)

    const [availableSkills, setAvailableSkills] = useState<string[]>([])
    const [availableTools, setAvailableTools] = useState<string[]>([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (open) {
            setLoading(true)
            Promise.all([fetchSkills(), fetchTools()])
                .then(([skills, tools]) => {
                    setAvailableSkills(skills)
                    setAvailableTools(tools)
                })
                .catch(console.error)
                .finally(() => setLoading(false))
        }
    }, [open])

    if (!currentAgent) return null

    const agentTools = (currentAgent as any).tools || []
    const agentSkills = (currentAgent as any).skills || []

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Zap className="w-5 h-5 text-amber-500" />
                        Agent 能力面板 ({currentAgent.name})
                    </DialogTitle>
                    <DialogDescription>
                        当前 Agent 拥有的以及系统中所有可用的工具和技能。
                    </DialogDescription>
                </DialogHeader>

                <ScrollArea className="max-h-[60vh] pr-4">
                    <div className="space-y-6">

                        {/* 该 Agent 拥有的能力 */}
                        <div className="space-y-3">
                            <h3 className="text-sm font-semibold flex items-center gap-2 text-primary">
                                <Zap className="w-4 h-4" /> 该 Agent 拥有的能力
                            </h3>
                            <div className="bg-muted/30 p-3 rounded-lg border space-y-4">
                                <div>
                                    <div className="text-xs text-muted-foreground mb-2">已装备工具 (Tools)</div>
                                    <div className="flex flex-wrap gap-2">
                                        {agentTools.length > 0 ? agentTools.map((t: string) => (
                                            <Badge key={t} variant="secondary" className="bg-blue-100 text-blue-700 hover:bg-blue-100">{t}</Badge>
                                        )) : <span className="text-xs text-muted-foreground italic">暂无工具</span>}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-xs text-muted-foreground mb-2">已装备技能 (Skills)</div>
                                    <div className="flex flex-wrap gap-2">
                                        {agentSkills.length > 0 ? agentSkills.map((s: string) => (
                                            <Badge key={s} variant="secondary" className="bg-amber-100 text-amber-700 hover:bg-amber-100">{s}</Badge>
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
                                    <div>
                                        <div className="text-xs text-muted-foreground mb-2">所有基础工具 (Core Tools)</div>
                                        <div className="flex flex-wrap gap-2">
                                            {availableTools.map(t => (
                                                <Badge key={t} variant="outline" className={agentTools.includes(t) ? "border-blue-500 text-blue-600 bg-blue-50" : ""}>
                                                    {t}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-muted-foreground mb-2">所有高级技能 (Advanced Skills)</div>
                                        <div className="flex flex-wrap gap-2">
                                            {availableSkills.map(s => (
                                                <Badge key={s} variant="outline" className={agentSkills.includes(s) ? "border-amber-500 text-amber-600 bg-amber-50" : ""}>
                                                    {s}
                                                </Badge>
                                            ))}
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
