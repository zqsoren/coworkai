import { useStore } from '../store'
import { WorkflowViewer } from './WorkflowViewer'
import { FileText, ChevronDown, ChevronRight, History, CheckCircle } from 'lucide-react'
import { ScrollArea } from "@/components/ui/scroll-area"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { useState } from 'react'
import { Badge } from "@/components/ui/badge"

function WorkflowHistoryItem({ workflow, index }: { workflow: any, index: number }) {
    const [isOpen, setIsOpen] = useState(false)
    return (
        <Collapsible open={isOpen} onOpenChange={setIsOpen} className="border border-border/50 rounded-lg bg-card/50 mb-3">
            <CollapsibleTrigger className="flex items-center justify-between w-full p-3 hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-2">
                    {isOpen ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                    <span className="text-sm font-medium">执行记录 #{index + 1}</span>
                    <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
                        {workflow.goal?.slice(0, 15)}...
                    </Badge>
                </div>
                <CheckCircle className="h-4 w-4 text-green-500" />
            </CollapsibleTrigger>
            <CollapsibleContent className="p-3 border-t border-border/50">
                <WorkflowViewer
                    workflow={workflow}
                    readOnly
                />
            </CollapsibleContent>
        </Collapsible>
    )
}

function LegacyPlanViewer({ workflow }: { workflow: any }) {
    const [isOpen, setIsOpen] = useState(true)

    return (
        <Collapsible open={isOpen} onOpenChange={setIsOpen} className="border border-border rounded-lg bg-card mb-4 shadow-sm">
            <CollapsibleTrigger className="flex items-center justify-between w-full p-4 hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-2 text-primary">
                    <FileText className="h-5 w-5" />
                    <span className="font-semibold">当前阶段计划</span>
                </div>
                {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </CollapsibleTrigger>
            <CollapsibleContent className="p-4 border-t border-border">
                <div className="space-y-4">
                    <div className="space-y-1">
                        <h4 className="text-sm font-medium text-muted-foreground">目标</h4>
                        <p className="text-sm">{workflow.goal || workflow.objective || '无'}</p>
                    </div>
                    {(workflow.deliverables || workflow.outputs) && (
                        <div className="space-y-1">
                            <h4 className="text-sm font-medium text-muted-foreground">产物</h4>
                            <p className="text-sm">{workflow.deliverables || workflow.outputs}</p>
                        </div>
                    )}
                    <div className="space-y-1">
                        <h4 className="text-sm font-medium text-muted-foreground">执行流程</h4>
                        {Array.isArray(workflow.process || workflow.steps) ? (
                            <ul className="list-decimal list-inside text-sm space-y-1">
                                {(workflow.process || workflow.steps).map((step: string, i: number) => (
                                    <li key={i} className="pl-1">{step}</li>
                                ))}
                            </ul>
                        ) : (
                            <p className="text-sm whitespace-pre-wrap">{workflow.process || workflow.steps || '无'}</p>
                        )}
                    </div>
                </div>
            </CollapsibleContent>
        </Collapsible>
    )
}

export function WorkflowReviewPanel() {
    const { pendingWorkflow, executeWorkflow, cancelWorkflow, approvedWorkflows, chatMode } = useStore()

    // If we have history or pending workflow, show the panel content
    const hasContent = pendingWorkflow || (approvedWorkflows && approvedWorkflows.length > 0)

    if (!hasContent) {
        return (
            <div className="flex-1 flex flex-col p-8 text-center items-center justify-center h-full">
                <FileText className="h-16 w-16 text-gray-300 mb-4 mx-auto" />
                <h3 className="text-lg font-semibold text-gray-700 mb-2">
                    暂无执行计划
                </h3>
                <p className="text-sm text-gray-500 max-w-md mx-auto">
                    在对话中生成的计划将显示在此处。
                </p>
            </div>
        )
    }

    return (
        <div className="flex-1 h-full flex flex-col overflow-hidden">
            <ScrollArea className="flex-1">
                <div className="p-4 space-y-6">
                    {/* History Section */}
                    {approvedWorkflows && approvedWorkflows.length > 0 && (
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-muted-foreground px-1">
                                <History className="h-4 w-4" />
                                <h3 className="text-sm font-medium">历史记录</h3>
                            </div>
                            {approvedWorkflows.map((wf, idx) => (
                                <WorkflowHistoryItem key={idx} workflow={wf} index={approvedWorkflows.length - 1 - idx} />
                            ))}
                        </div>
                    )}

                    {/* Pending / Active Section */}
                    {pendingWorkflow && (
                        <div className="space-y-2">
                            <div className="flex items-center gap-2 text-primary px-1 mb-2">
                                <FileText className="h-4 w-4" />
                                <h3 className="text-sm font-medium">
                                    {chatMode === 'legacy' ? "当前任务" : "待审批计划"}
                                </h3>
                            </div>

                            {chatMode === 'legacy' ? (
                                <LegacyPlanViewer workflow={pendingWorkflow} />
                            ) : (
                                <WorkflowViewer
                                    workflow={pendingWorkflow}
                                    onExecute={executeWorkflow}
                                    onCancel={cancelWorkflow}
                                />
                            )}
                        </div>
                    )}
                </div>
            </ScrollArea>
        </div>
    )
}
