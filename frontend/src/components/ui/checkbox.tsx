import * as React from "react"
import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

const Checkbox = React.forwardRef<
    HTMLInputElement,
    React.InputHTMLAttributes<HTMLInputElement> & { onCheckedChange?: (checked: boolean) => void }
>(({ className, onCheckedChange, onChange, ...props }, ref) => {

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (onCheckedChange) {
            onCheckedChange(e.target.checked)
        }
        if (onChange) {
            onChange(e)
        }
    }

    return (
        <div className="relative flex items-center">
            <input
                type="checkbox"
                className={cn(
                    "peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none checked:bg-primary checked:text-primary-foreground",
                    className
                )}
                onChange={handleChange}
                ref={ref}
                {...props}
            />
            <Check className="absolute left-0 top-0 h-4 w-4 hidden peer-checked:block pointer-events-none text-primary-foreground" />
        </div>
    )
})
Checkbox.displayName = "Checkbox"

export { Checkbox }
