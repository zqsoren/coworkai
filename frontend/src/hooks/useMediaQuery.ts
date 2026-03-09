import { useState, useEffect } from "react"

export function useMediaQuery(query: string): boolean {
    const [matches, setMatches] = useState(() => {
        if (typeof window !== "undefined") {
            return window.matchMedia(query).matches
        }
        return false
    })

    useEffect(() => {
        const mediaQuery = window.matchMedia(query)
        const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
        mediaQuery.addEventListener("change", handler)
        setMatches(mediaQuery.matches)
        return () => mediaQuery.removeEventListener("change", handler)
    }, [query])

    return matches
}

export function useIsTablet(): boolean {
    return useMediaQuery("(max-width: 1024px)")
}

export function useIsMobile(): boolean {
    return useMediaQuery("(max-width: 768px)")
}
