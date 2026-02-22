import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { useState, useEffect } from 'react'
import { Workflow, Zap } from 'lucide-react'
import { DEFAULT_WORKFLOW_SUPERVISOR_PROMPT, DEFAULT_LEGACY_SUPERVISOR_PROMPT } from '../constants/prompts'

interface Group {
    id: string
    name: string
    supervisor_id: string
    members: string[]
    supervisor_prompt?: string
    workflow_supervisor_prompt?: string
}

interface SupervisorPromptModalProps {
    open: boolean
    onClose: () => void
    currentGroup: Group
    onSave: (prompts: {
        supervisor_prompt?: string
        workflow_supervisor_prompt?: string
    }) => Promise<void>
}

export function SupervisorPromptModal({
    open,
    onClose,
    currentGroup,
    onSave
}: SupervisorPromptModalProps) {
    const [workflowPrompt, setWorkflowPrompt] = useState("")
    const [legacyPrompt, setLegacyPrompt] = useState("")
    const [activeTab, setActiveTab] = useState<'workflow' | 'legacy'>('workflow')
    const [isSaving, setIsSaving] = useState(false)

    // Load prompts when modal opens or group changes
    useEffect(() => {
        if (open && currentGroup) {
            setWorkflowPrompt(
                currentGroup.workflow_supervisor_prompt || DEFAULT_WORKFLOW_SUPERVISOR_PROMPT
            )
            setLegacyPrompt(
                currentGroup.supervisor_prompt || DEFAULT_LEGACY_SUPERVISOR_PROMPT
            )
        }
    }, [open, currentGroup])

    const handleSave = async () => {
        setIsSaving(true)
        try {
            await onSave({
                workflow_supervisor_prompt: workflowPrompt,
                supervisor_prompt: legacyPrompt
            })
            onClose()
        } catch (error) {
            console.error('Failed to save prompts:', error)
        } finally {
            setIsSaving(false)
        }
    }

    const handleCancel = () => {
        // Reset to original values
        setWorkflowPrompt(
            currentGroup.workflow_supervisor_prompt || DEFAULT_WORKFLOW_SUPERVISOR_PROMPT
        )
        setLegacyPrompt(
            currentGroup.supervisor_prompt || DEFAULT_LEGACY_SUPERVISOR_PROMPT
        )
        onClose()
    }

    return (
        <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleCancel()}>
            <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>编辑 Supervisor 提示词</DialogTitle>
                    <p className="text-sm text-gray-600 mt-1">
                        分别配置工作流模式和逐步决策模式的 Supervisor 行为
                    </p>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'workflow' | 'legacy')} className="flex-1 flex flex-col">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="workflow" className="flex items-center gap-2">
                            <Workflow className="h-4 w-4" />
                            工作流模式
                        </TabsTrigger>
                        <TabsTrigger value="legacy" className="flex items-center gap-2">
                            <Zap className="h-4 w-4" />
                            逐步决策模式
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="workflow" className="flex-1 mt-4">
                        <div className="space-y-3">
                            <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-1">🔄 工作流模式提示词</h4>
                                <p className="text-xs text-gray-600 mb-2">
                                    用于生成执行计划。Supervisor 会一次性规划所有步骤、分配角色和审核流程。
                                </p>
                            </div>
                            <textarea
                                value={workflowPrompt}
                                onChange={(e) => setWorkflowPrompt(e.target.value)}
                                className="w-full h-80 px-3 py-2 border rounded-md text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500"
                                placeholder="输入工作流模式的 Supervisor 提示词..."
                            />
                        </div>
                    </TabsContent>

                    <TabsContent value="legacy" className="flex-1 mt-4">
                        <div className="space-y-3">
                            <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-1">⚡ 逐步决策模式提示词</h4>
                                <p className="text-xs text-gray-600 mb-2">
                                    用于实时决策。Supervisor 每轮分析历史，动态决定下一个发言者和任务。
                                </p>
                            </div>
                            <textarea
                                value={legacyPrompt}
                                onChange={(e) => setLegacyPrompt(e.target.value)}
                                className="w-full h-80 px-3 py-2 border rounded-md text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="输入逐步决策模式的 Supervisor 提示词..."
                            />
                        </div>
                    </TabsContent>
                </Tabs>

                <DialogFooter className="mt-4">
                    <Button variant="outline" onClick={handleCancel} disabled={isSaving}>
                        取消
                    </Button>
                    <Button onClick={handleSave} disabled={isSaving}>
                        {isSaving ? '保存中...' : '保存'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
