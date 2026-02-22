import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Plus, Users, Crown, Check } from "lucide-react"
import { useStore } from "@/store"
import { cn } from "@/lib/utils"

export function NewGroupModal() {
    const { agents, createGroup } = useStore()
    const [open, setOpen] = useState(false)
    const [groupName, setGroupName] = useState("")
    const [selectedMembers, setSelectedMembers] = useState<string[]>([])
    const [supervisorId, setSupervisorId] = useState<string>("")
    const [isCreating, setIsCreating] = useState(false)

    const toggleMember = (agentId: string) => {
        setSelectedMembers(prev => {
            const next = prev.includes(agentId)
                ? prev.filter(id => id !== agentId)
                : [...prev, agentId]

            // Auto-select supervisor if none selected and we have members
            if (!supervisorId && next.length > 0) {
                setSupervisorId(next[0])
            }
            // If removed member was supervisor, re-assign to first available or clear
            else if (supervisorId === agentId) {
                setSupervisorId(next.length > 0 ? next[0] : "")
            }

            return next
        })
    }

    const handleCreate = async () => {
        if (!groupName.trim() || selectedMembers.length < 2 || !supervisorId) return
        setIsCreating(true)
        try {
            await createGroup(groupName.trim(), selectedMembers, supervisorId)
            setGroupName("")
            setSelectedMembers([])
            setSupervisorId("")
            setOpen(false)
        } catch (e) {
            console.error("Failed to create group:", e)
        } finally {
            setIsCreating(false)
        }
    }

    const canCreate = groupName.trim() && selectedMembers.length >= 2 && supervisorId

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" className="w-full justify-start px-3 py-2 text-sm font-normal text-gray-600 hover:shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] rounded-xl transition-shadow duration-300 mt-1 gap-3 hover:bg-transparent opacity-60 hover:opacity-100">
                    <Plus className="w-4 h-4 shrink-0" /> <span className="truncate">New Group</span>
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5 text-green-600" />
                        新建群聊
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Group Name */}
                    <div className="space-y-2">
                        <Label className="text-xs font-medium">群聊名称</Label>
                        <Input
                            placeholder="例如：内容创作团队"
                            value={groupName}
                            onChange={(e) => setGroupName(e.target.value)}
                        />
                    </div>

                    {/* Member Selection */}
                    <div className="space-y-2">
                        <Label className="text-xs font-medium">
                            选择成员 ({selectedMembers.length} 已选，至少 2 人)
                        </Label>
                        <ScrollArea className="h-48 rounded-md border p-2">
                            <div className="space-y-1">
                                {agents.map((agent) => {
                                    const isSelected = selectedMembers.includes(agent.id)
                                    const isSupervisor = supervisorId === agent.id

                                    return (
                                        <div
                                            key={agent.id}
                                            className={cn(
                                                "flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors",
                                                isSelected ? "bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800" : "hover:bg-muted/50"
                                            )}
                                            onClick={() => toggleMember(agent.id)}
                                        >
                                            {/* Checkbox */}
                                            <div className={cn(
                                                "h-4 w-4 rounded border flex items-center justify-center shrink-0 transition-colors",
                                                isSelected ? "bg-blue-600 border-blue-600" : "border-muted-foreground/30"
                                            )}>
                                                {isSelected && <Check className="h-3 w-3 text-white" />}
                                            </div>

                                            {/* Agent Info */}
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm font-medium truncate flex items-center gap-1">
                                                    {agent.name}
                                                    {isSupervisor && <Crown className="h-3 w-3 text-amber-500" />}
                                                </div>
                                                <div className="text-[10px] text-muted-foreground truncate">
                                                    {agent.system_prompt?.substring(0, 40) || "AI Agent"}
                                                </div>
                                            </div>

                                            {/* Set as Supervisor */}
                                            {isSelected && (
                                                <Button
                                                    variant={isSupervisor ? "default" : "ghost"}
                                                    size="sm"
                                                    className={cn(
                                                        "h-6 text-[10px] px-2 shrink-0",
                                                        isSupervisor ? "bg-amber-500 hover:bg-amber-600 text-white" : ""
                                                    )}
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        setSupervisorId(isSupervisor ? "" : agent.id)
                                                    }}
                                                >
                                                    <Crown className="h-3 w-3 mr-1" />
                                                    {isSupervisor ? "主持人" : "设为主持人"}
                                                </Button>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* Validation Messages */}
                    {selectedMembers.length > 0 && !supervisorId && (
                        <p className="text-xs text-amber-600 flex items-center gap-1">
                            <Crown className="h-3 w-3" />
                            请从已选成员中指定一位主持人
                        </p>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
                    <Button
                        onClick={handleCreate}
                        disabled={!canCreate || isCreating}
                        className="bg-green-600 hover:bg-green-700"
                    >
                        {isCreating ? "创建中..." : "创建群聊"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
