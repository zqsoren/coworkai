import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { GroupMembersPanel } from './GroupMembersPanel'
import { WorkflowReviewPanel } from './WorkflowReviewPanel'
import { useStore } from '../store'
import { Users, FileText } from 'lucide-react'

export function GroupTabs() {
    const { pendingWorkflow } = useStore()

    return (
        <Tabs defaultValue="members" className="h-full flex flex-col">
            <TabsList className="grid w-[calc(100%-2rem)] grid-cols-2 mx-auto mt-2 flex-shrink-0">
                <TabsTrigger value="members" className="text-xs">
                    <Users className="h-4 w-4 mr-1.5" />
                    成员管理
                </TabsTrigger>
                <TabsTrigger value="review" className="text-xs relative">
                    <FileText className="h-4 w-4 mr-1.5" />
                    批阅
                    {pendingWorkflow && (
                        <span className="absolute -top-1 -right-1 flex h-5 w-5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-5 w-5 bg-red-500 items-center justify-center">
                                <span className="text-[10px] text-white font-bold">1</span>
                            </span>
                        </span>
                    )}
                </TabsTrigger>
            </TabsList>

            <TabsContent value="members" className="mt-0 flex-1 flex flex-col overflow-hidden data-[state=inactive]:hidden">
                <GroupMembersPanel />
            </TabsContent>

            <TabsContent value="review" className="mt-0 flex-1 flex flex-col overflow-hidden data-[state=inactive]:hidden">
                <WorkflowReviewPanel />
            </TabsContent>
        </Tabs>
    )
}
