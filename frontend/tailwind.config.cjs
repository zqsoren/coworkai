/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
    theme: {
        extend: {
            borderRadius: {
                lg: 'var(--radius)',
                md: 'calc(var(--radius) - 2px)',
                sm: 'calc(var(--radius) - 4px)'
            },
            colors: {
                background: 'hsl(var(--background))',
                foreground: 'hsl(var(--foreground))',
                card: {
                    DEFAULT: 'hsl(var(--card))',
                    foreground: 'hsl(var(--card-foreground))'
                },
                popover: {
                    DEFAULT: 'hsl(var(--popover))',
                    foreground: 'hsl(var(--popover-foreground))'
                },
                primary: {
                    DEFAULT: 'hsl(var(--primary))',
                    foreground: 'hsl(var(--primary-foreground))'
                },
                secondary: {
                    DEFAULT: 'hsl(var(--secondary))',
                    foreground: 'hsl(var(--secondary-foreground))'
                },
                muted: {
                    DEFAULT: 'hsl(var(--muted))',
                    foreground: 'hsl(var(--muted-foreground))'
                },
                accent: {
                    DEFAULT: 'hsl(var(--accent))',
                    foreground: 'hsl(var(--accent-foreground))'
                },
                destructive: {
                    DEFAULT: 'hsl(var(--destructive))',
                    foreground: 'hsl(var(--destructive-foreground))'
                },
                border: 'hsl(var(--border))',
                input: 'hsl(var(--input))',
                ring: 'hsl(var(--ring))',
                chart: {
                    '1': 'hsl(var(--chart-1))',
                    '2': 'hsl(var(--chart-2))',
                    '3': 'hsl(var(--chart-3))',
                    '4': 'hsl(var(--chart-4))',
                    '5': 'hsl(var(--chart-5))'
                }
            },
            typography: {
                DEFAULT: {
                    css: {
                        h1: {
                            fontSize: '1.25rem', // 调小一点
                            marginTop: '1.5rem',
                            marginBottom: '1rem',
                            fontWeight: '700',
                        },
                        h2: {
                            fontSize: '1.1rem',
                            marginTop: '1.25rem',
                            marginBottom: '0.75rem',
                        },
                        h3: {
                            fontSize: '1rem',
                            marginTop: '1rem',
                            marginBottom: '0.5rem',
                        },
                    },
                },
                // 强制覆盖 Chat.tsx 中使用的 prose-sm (小号排版) 模式
                sm: {
                    css: {
                        h1: {
                            fontSize: '1.15rem', // 这是您反馈的那行字的大小
                            marginTop: '1rem',
                            marginBottom: '0.5rem',
                            lineHeight: '1',
                        },
                        h2: {
                            fontSize: '1.1rem',
                            marginTop: '0.5rem',
                            marginBottom: '0.3rem',
                            fontWeight: '700',
                        },
                        h3: {
                            fontSize: '0.9rem',
                            marginTop: '0.4rem',
                            marginBottom: '0.3rem',
                            fontWeight: '700',
                        },
                        h4: {
                            fontSize: '0.9rem',
                            marginTop: '0.3rem',
                            marginBottom: '0.2rem',
                            fontWeight: '700',
                        },
                    },
                },
            },
        }
    },
    plugins: [
        require("tailwindcss-animate"),
        require("@tailwindcss/typography")
    ],
}
