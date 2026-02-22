import { useStore } from "@/store"
import { Button } from "@/components/ui/button"
import { Check, X, FileDiff } from "lucide-react"
import { translations } from "@/lib/i18n"

export function PendingChangesList() {
    const { pendingChanges, applyChange, language } = useStore()
    const t = translations[language].rightPanel

    if (pendingChanges.length === 0) {
        return (
            <div className="text-center text-muted-foreground p-4 text-sm italic">
                {t.noChanges}
            </div>
        )
    }

    return (
        <div className="space-y-4 p-4">
            {pendingChanges.map((change, idx) => (
                <div key={idx} className="border rounded-lg p-3 bg-card shadow-sm">
                    <div className="flex items-center gap-2 font-medium text-sm mb-2 text-primary">
                        <FileDiff className="w-4 h-4" />
                        <span className="truncate">{change.file_path}</span>
                    </div>

                    <div className="text-xs bg-muted p-2 rounded max-h-32 overflow-auto font-mono mb-3">
                        {/* Simple Diff View - simplified for now */}
                        {change.diff_lines.slice(0, 5).map((l, i) => (
                            <div key={i} className={l.startsWith('+') ? 'text-green-600' : l.startsWith('-') ? 'text-red-600' : 'text-muted-foreground'}>
                                {l}
                            </div>
                        ))}
                        {change.diff_lines.length > 5 && <div className="text-muted-foreground">...</div>}
                    </div>

                    <div className="flex gap-2">
                        <Button size="sm" className="flex-1 bg-green-600 hover:bg-green-700 text-white" onClick={() => applyChange(change)}>
                            <Check className="w-4 h-4 mr-1" /> {t.approve}
                        </Button>
                        <Button size="sm" variant="outline" className="flex-1 text-red-600 border-red-200 hover:bg-red-50" onClick={() => {/* Reject logic in store/api? For now assume ignore */ }}>
                            <X className="w-4 h-4 mr-1" /> {t.reject}
                        </Button>
                    </div>
                </div>
            ))}
        </div>
    )
}
