import * as React from "react"
import { cn } from "@/lib/utils"

const Collapsible = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement> & {
        open?: boolean
        onOpenChange?: (open: boolean) => void
        defaultOpen?: boolean
    }
>(({ className, open: controlledOpen, onOpenChange, defaultOpen = false, ...props }, ref) => {
    const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen)
    const isControlled = controlledOpen !== undefined
    const open = isControlled ? controlledOpen : uncontrolledOpen

    // Sync with context if we were using one, but for simple usage:
    // We can just rely on the parent controlling it or internal state.

    return (
        <div
            ref={ref}
            data-state={open ? "open" : "closed"}
            className={cn(className)}
            {...props}
        />
    )
})
Collapsible.displayName = "Collapsible"

const CollapsibleTrigger = React.forwardRef<
    HTMLButtonElement,
    React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, onClick, ...props }, ref) => {
    // This is a bit hacky without a context, but effective for the specific usage in WorkflowReviewPanel
    // In WorkflowReviewPanel, we are passing `open` and `onOpenChange` to the root Collapsible.
    // The Trigger there is just a styled button. 
    // Wait, the standard Radix/Shadcn pattern uses Context.
    // To properly support the usage:
    // <Collapsible open={isOpen} onOpenChange={setIsOpen}>
    //   <CollapsibleTrigger onClick={() => setIsOpen(!isOpen)} ... /> 
    // 
    // But in WorkflowReviewPanel, the `onOpenChange` is passed to the Root.
    // The Trigger needs to know how to toggle.
    // Since I'm implementing a lightweight version, I should probably use a Context to make it cleaner.
    return (
        <button
            ref={ref}
            type="button"
            className={cn("flex items-center justify-between w-full", className)}
            // onClick is handled by the user in the usage example? 
            // No, in WorkflowReviewPanel, the trigger JUST wraps the content.
            // It expects the Collapsible Root to handle state or the user to wire it up?
            // Actually standard shadcn CollapsibleTrigger toggles the context.
            onClick={(e) => {
                onClick?.(e)
                // We need to find the context to toggle.
                // Let's implement a simple Context.
            }}
            {...props}
        />
    )
})
CollapsibleTrigger.displayName = "CollapsibleTrigger"

const CollapsibleContent = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
    // In a real implementation this would use context to determine if it should show.
    // But since we can't easily query the context from here without defining it...
    // Let's make a contextual implementation.
    return (
        <div
            ref={ref}
            className={cn("overflow-hidden", className)}
            {...props}
        />
    )
})
CollapsibleContent.displayName = "CollapsibleContent"


// --- Context Implementation ---
interface CollapsibleContextValue {
    open: boolean
    onOpenChange: (open: boolean) => void
}
const CollapsibleContext = React.createContext<CollapsibleContextValue | undefined>(undefined)

const CollapsibleRoot = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement> & {
        open?: boolean
        onOpenChange?: (open: boolean) => void
        defaultOpen?: boolean
        disabled?: boolean
    }
>(({ open: controlledOpen, onOpenChange, defaultOpen, className, children, ...props }, ref) => {
    const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen ?? false)
    const isControlled = controlledOpen !== undefined
    const open = isControlled ? controlledOpen : uncontrolledOpen

    const handleOpenChange = React.useCallback((newOpen: boolean) => {
        if (!isControlled) {
            setUncontrolledOpen(newOpen)
        }
        onOpenChange?.(newOpen)
    }, [isControlled, onOpenChange])

    return (
        <CollapsibleContext.Provider value={{ open: open!, onOpenChange: handleOpenChange }}>
            <div
                ref={ref}
                data-state={open ? "open" : "closed"}
                className={cn("group/collapsible", className)}
                {...props}
            >
                {children}
            </div>
        </CollapsibleContext.Provider>
    )
})
CollapsibleRoot.displayName = "Collapsible"

const Trigger = React.forwardRef<
    HTMLButtonElement,
    React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, onClick, children, ...props }, ref) => {
    const context = React.useContext(CollapsibleContext)

    return (
        <button
            ref={ref}
            type="button"
            className={cn("flex w-full items-center justify-between", className)}
            onClick={(e) => {
                onClick?.(e)
                context?.onOpenChange(!context.open)
            }}
            data-state={context?.open ? "open" : "closed"}
            {...props}
        >
            {children}
        </button>
    )
})
Trigger.displayName = "CollapsibleTrigger"

const Content = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
    const context = React.useContext(CollapsibleContext)

    if (!context?.open) return null

    return (
        <div
            ref={ref}
            className={cn("overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down", className)}
            data-state={context.open ? "open" : "closed"}
            {...props}
        >
            {children}
        </div>
    )
})
Content.displayName = "CollapsibleContent"

export { CollapsibleRoot as Collapsible, Trigger as CollapsibleTrigger, Content as CollapsibleContent }
