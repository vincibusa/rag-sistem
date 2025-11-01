'use client'

import * as React from 'react'
import { FileText, Home, Search, Upload, Settings, Database } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarRail,
} from '@/components/ui/sidebar'

const menuItems = [
	{
		title: 'Dashboard',
		url: '/dashboard',
		icon: Home,
	},
	{
		title: 'Upload Documenti',
		url: '/dashboard/upload',
		icon: Upload,
	},
	{
		title: 'Documenti',
		url: '/dashboard/documents',
		icon: FileText,
	},
	{
		title: 'Chat AI',
		url: '/dashboard/search',
		icon: Search,
	},
	{
		title: 'Database',
		url: '/dashboard/database',
		icon: Database,
	},
	{
		title: 'Impostazioni',
		url: '/dashboard/settings',
		icon: Settings,
	},
]

export function AppSidebar() {
	const pathname = usePathname()

	return (
		<Sidebar>
			<SidebarContent>
				<SidebarGroup>
					<SidebarGroupLabel className="text-xs sm:text-sm">
						Medit RAG
					</SidebarGroupLabel>
					<SidebarGroupContent>
						<SidebarMenu>
							{menuItems.map((item) => (
								<SidebarMenuItem key={item.title}>
									<SidebarMenuButton asChild isActive={pathname === item.url}>
										<Link href={item.url}>
											<item.icon className="h-4 w-4 sm:h-5 sm:w-5" />
											<span className="text-sm sm:text-base">{item.title}</span>
										</Link>
									</SidebarMenuButton>
								</SidebarMenuItem>
							))}
						</SidebarMenu>
					</SidebarGroupContent>
				</SidebarGroup>
			</SidebarContent>
			<SidebarFooter>
				<div className="p-3 sm:p-4 text-xs text-muted-foreground">
					v1.0.0 - RAG System
				</div>
			</SidebarFooter>
			<SidebarRail />
		</Sidebar>
	)
}


