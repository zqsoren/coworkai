import { useState } from 'react'
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import {
    UserPlus,
    MoreHorizontal,
    Crown,
    UserMinus
} from 'lucide-react'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useStore } from '../store'
import { SupervisorPromptModal } from './SupervisorPromptModal'

export function GroupMembersPanel() {
    const {
        currentGroupId,
        groups,
        agents,
        updateGroupSettings
    } = useStore()

    const currentGroup = groups.find(g => g.id === currentGroupId)

    const [showAddMember, setShowAddMember] = useState(false)
    const [selectedNewMembers, setSelectedNewMembers] = useState<string[]>([])
    const [isPromptModalOpen, setIsPromptModalOpen] = useState(false)

    console.log("[GroupMembersPanel] Rendered. Group:", currentGroupId)

    if (!currentGroup) {
        return (
            <div className="p-4 text-center text-gray-500">
                <p>请先选择一个群聊</p>
            </div>
        )
    }

    const supervisorAgent = agents.find(a => a.id === currentGroup.supervisor_id)
    const memberAgents = agents.filter(a => currentGroup.members?.includes(a.id))
    const availableAgents = agents.filter(
        a => !currentGroup.members?.includes(a.id) && a.id !== currentGroup.supervisor_id
    )

    const handleSavePrompts = async (prompts: {
        supervisor_prompt?: string
        workflow_supervisor_prompt?: string
    }) => {
        if (!currentGroupId) return
        await updateGroupSettings(currentGroupId, prompts)
    }

    const handleOpenAddMember = () => {
        setSelectedNewMembers([])
        setShowAddMember(true)
    }

    const handleAddMembers = async () => {
        if (!currentGroupId || selectedNewMembers.length === 0) return

        const updatedMembers = [...(currentGroup.members || []), ...selectedNewMembers]
        await updateGroupSettings(currentGroupId, {
            members: updatedMembers
        })
        setShowAddMember(false)
        setSelectedNewMembers([])
    }

    const toggleNewMember = (agentId: string) => {
        setSelectedNewMembers(prev =>
            prev.includes(agentId)
                ? prev.filter(id => id !== agentId)
                : [...prev, agentId]
        )
    }

    const handleRemoveMember = async (agentId: string) => {
        if (!currentGroupId) return
        const updatedMembers = currentGroup.members?.filter(id => id !== agentId) || []
        await updateGroupSettings(currentGroupId, {
            members: updatedMembers
        })
    }

    const handleSetSupervisor = async (newSupervisorId: string) => {
        if (!currentGroupId) return

        const oldSupervisorId = currentGroup.supervisor_id

        // Ensure we don't duplicate when swapping
        let updatedMembers = currentGroup.members?.filter(id => id !== newSupervisorId) || []
        if (oldSupervisorId) {
            updatedMembers.push(oldSupervisorId)
        }

        // Deduplicate just in case
        updatedMembers = Array.from(new Set(updatedMembers))

        await updateGroupSettings(currentGroupId, {
            supervisor_id: newSupervisorId,
            members: updatedMembers
        })
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            {/* Supervisor Prompt Modal */}
            <SupervisorPromptModal
                open={isPromptModalOpen}
                onClose={() => setIsPromptModalOpen(false)}
                currentGroup={currentGroup}
                onSave={handleSavePrompts}
            />

            <div className="flex-1 overflow-auto">
                <div className="px-4 py-6 space-y-8">
                    {/* Supervisor Section (Black Theme) */}
                    <div>
                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-3 px-1">
                            主持人
                        </div>

                        {supervisorAgent ? (
                            <div className="bg-white rounded-full p-2 pr-2 flex items-center gap-3 border border-gray-200 shadow-sm relative group">
                                <div className="w-10 h-10 rounded-full bg-black text-white flex items-center justify-center shrink-0 shadow-sm">
                                    <Crown className="w-4 h-4" />
                                </div>
                                <div className="flex-1 min-w-0 pr-2">
                                    <div className="font-semibold text-sm text-gray-900 truncate">{supervisorAgent.name}</div>
                                    <div className="text-[10px] text-gray-500 font-medium truncate flex items-center gap-1">
                                        Supervisor
                                        {(currentGroup.supervisor_prompt || currentGroup.workflow_supervisor_prompt) && (
                                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 block" title="Custom Prompt Active" />
                                        )}
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 rounded-full text-gray-400 hover:text-black hover:bg-gray-100 transition-colors"
                                    onClick={() => setIsPromptModalOpen(true)}
                                >
                                    <MoreHorizontal className="h-4 w-4" />
                                </Button>
                            </div>
                        ) : (
                            <div className="bg-gray-50 border border-dashed border-gray-300 rounded-full p-2 text-center text-xs text-gray-500">
                                未设置主持人
                            </div>
                        )}
                    </div>

                    {/* Members Section (Pill Style) */}
                    <div>
                        <div className="flex items-center justify-between mb-3 px-1">
                            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                                成员 ({memberAgents.length})
                            </h3>
                            <button
                                onClick={handleOpenAddMember}
                                className="text-[10px] text-blue-600 font-medium hover:underline flex items-center gap-1"
                            >
                                <UserPlus className="h-3 w-3" /> 邀请成员
                            </button>
                        </div>

                        {/* Add Member Panel */}
                        {showAddMember && (
                            <div className="mb-4 p-3 bg-white border border-gray-100 rounded-xl shadow-sm animate-in fade-in slide-in-from-top-2">
                                <p className="text-xs font-semibold mb-2 text-gray-700">选择成员</p>
                                <ScrollArea className="max-h-40">
                                    <div className="space-y-1">
                                        {availableAgents.map(agent => (
                                            <div
                                                key={agent.id}
                                                className={`
                                                  p-2 rounded-lg cursor-pointer transition-all border text-sm flex items-center justify-between
                                                  ${selectedNewMembers.includes(agent.id)
                                                        ? 'bg-blue-50 border-blue-200 text-blue-700'
                                                        : 'bg-gray-50 border-transparent hover:bg-gray-100 text-gray-700'}
                                                `}
                                                onClick={() => toggleNewMember(agent.id)}
                                            >
                                                <span className="font-medium">{agent.name}</span>
                                                {selectedNewMembers.includes(agent.id) && <div className="w-2 h-2 rounded-full bg-blue-500" />}
                                            </div>
                                        ))}
                                        {availableAgents.length === 0 && (
                                            <p className="text-xs text-gray-400 italic text-center py-2">无更多可用成员</p>
                                        )}
                                    </div>
                                </ScrollArea>
                                <div className="flex gap-2 mt-3 pt-2 border-t border-gray-50">
                                    <Button size="sm" className="h-7 text-xs bg-black hover:bg-gray-800" onClick={handleAddMembers} disabled={selectedNewMembers.length === 0}>
                                        添加
                                    </Button>
                                    <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setShowAddMember(false)}>
                                        取消
                                    </Button>
                                </div>
                            </div>
                        )}

                        {/* Members List */}
                        <div className="space-y-2">
                            {memberAgents.length === 0 ? (
                                <p className="text-xs text-gray-400 text-center py-4 italic">暂无成员</p>
                            ) : (
                                memberAgents.map(agent => (
                                    <div
                                        key={agent.id}
                                        className="bg-gray-50 rounded-full p-2 pr-2 flex items-center gap-3 border border-gray-100 hover:bg-white hover:border-gray-200 hover:shadow-sm transition-all group"
                                    >
                                        <Avatar className="h-9 w-9 bg-white border border-gray-100 text-gray-600">
                                            <AvatarFallback className="text-xs font-bold">{agent.name[0]}</AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium text-sm text-gray-700 truncate">
                                                {agent.name}
                                            </div>
                                            <div className="text-[10px] text-gray-400 truncate">Member</div>
                                        </div>

                                        {/* Dropdown Menu */}
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 rounded-full text-gray-300 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                                                >
                                                    <MoreHorizontal className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end" className="w-40">
                                                <DropdownMenuItem onClick={() => handleSetSupervisor(agent.id)}>
                                                    <Crown className="w-3.5 h-3.5 mr-2 text-amber-500" />
                                                    <span>设为主持人</span>
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={() => handleRemoveMember(agent.id)}
                                                    className="text-red-600 focus:text-red-600"
                                                >
                                                    <UserMinus className="w-3.5 h-3.5 mr-2" />
                                                    <span>移出群聊</span>
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
