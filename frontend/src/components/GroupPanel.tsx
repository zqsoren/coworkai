import { useStore } from '../store'
import { GroupTabs } from './GroupTabs'
import { Users } from 'lucide-react'

export function GroupPanel() {
    const { currentGroupId, groups } = useStore()

    const currentGroup = groups.find(g => g.id === currentGroupId)

    if (!currentGroup) {
        return (
            <div className="h-full flex flex-col items-center justify-center p-4 text-center">
                <Users className="h-16 w-16 text-gray-300 mb-3" />
                <p className="text-sm text-gray-600">请先选择或创建一个群聊</p>
            </div>
        )
    }

    return (
        <div className="h-full flex flex-col">


            {/* Group Tabs */}
            <div className="flex-1 overflow-hidden">
                <GroupTabs />
            </div>
        </div>
    )
}
