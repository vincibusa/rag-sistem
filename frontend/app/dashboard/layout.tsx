import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/app-sidebar'
import { ThemeToggle } from '@/components/theme-toggle'
import { Separator } from '@/components/ui/separator'

export default function DashboardLayout({
	children,
}: {
	children: React.ReactNode
}) {
	return (
		<SidebarProvider>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-14 sm:h-16 shrink-0 items-center gap-2 border-b px-3 sm:px-4">
					<SidebarTrigger className="-ml-1 h-8 w-8 sm:h-9 sm:w-9" />
					<Separator orientation="vertical" className="mr-1 sm:mr-2 h-4 hidden sm:block" />
					<div className="flex flex-1 items-center justify-between min-w-0">
						<h1 className="text-base sm:text-lg font-semibold truncate">
							Medit RAG System
						</h1>
						<div className="flex items-center gap-2 flex-shrink-0">
							<ThemeToggle />
						</div>
					</div>
				</header>
				<div className="flex flex-1 flex-col gap-3 sm:gap-4 p-3 sm:p-4 sm:pt-6">
					{children}
				</div>
			</SidebarInset>
		</SidebarProvider>
	)
}
