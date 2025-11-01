'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Database, FileText, Search, Upload, Activity, CheckCircle2, Clock, AlertCircle, Sparkles, TrendingUp, Zap } from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

// Mock data - sostituire con dati reali
const stats = {
	totalDocuments: 0,
	processed: 0,
	ragQueries: 0,
	chunks: 0,
}

const systemStatus = [
	{ name: 'Backend API', status: 'online' as const },
	{ name: 'Vector Database', status: 'pending' as const },
	{ name: 'Document Processing', status: 'pending' as const },
]

const recentActivity: Array<{
	id: string
	type: 'upload' | 'process' | 'search'
	description: string
	timestamp: string
}> = []

export default function DashboardPage() {
	const [isLoading] = useState(false)

	const getStatusColor = (status: 'online' | 'pending' | 'error') => {
		switch (status) {
			case 'online':
				return 'text-green-600 dark:text-green-400'
			case 'pending':
				return 'text-yellow-600 dark:text-yellow-400'
			case 'error':
				return 'text-red-600 dark:text-red-400'
			default:
				return 'text-muted-foreground'
		}
	}

	const getStatusIcon = (status: 'online' | 'pending' | 'error') => {
		switch (status) {
			case 'online':
				return <CheckCircle2 className="h-4 w-4" />
			case 'pending':
				return <Clock className="h-4 w-4" />
			case 'error':
				return <AlertCircle className="h-4 w-4" />
			default:
				return null
		}
	}

	const statCards = [
		{
			title: 'Documenti Totali',
			value: stats.totalDocuments,
			description: stats.totalDocuments === 0 ? 'Nessun documento caricato' : `${stats.processed} elaborati`,
			icon: FileText,
			color: 'text-blue-600 dark:text-blue-400',
			bgColor: 'bg-blue-500/10',
		},
		{
			title: 'Elaborati',
			value: stats.processed,
			description: 'Pronti per ricerca',
			icon: Upload,
			color: 'text-green-600 dark:text-green-400',
			bgColor: 'bg-green-500/10',
		},
		{
			title: 'Ricerche RAG',
			value: stats.ragQueries,
			description: 'Ricerche effettuate',
			icon: Search,
			color: 'text-purple-600 dark:text-purple-400',
			bgColor: 'bg-purple-500/10',
		},
		{
			title: 'Database Vettoriale',
			value: stats.chunks,
			description: 'Chunk memorizzati',
			icon: Database,
			color: 'text-orange-600 dark:text-orange-400',
			bgColor: 'bg-orange-500/10',
		},
	]

	return (
		<div className="space-y-4 md:space-y-6">
			{/* Header */}
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
					<Sparkles className="h-6 w-6 text-primary" />
					Dashboard
				</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Panoramica del sistema di gestione documenti
				</p>
			</div>

			{/* Statistiche - Grid mobile-first */}
			<div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
				{statCards.map((stat) => (
					<Card key={stat.title}>
						<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
							<CardTitle className="text-xs sm:text-sm font-medium">
								{stat.title}
							</CardTitle>
							<div className={cn('p-2 rounded-lg', stat.bgColor)}>
								<stat.icon className={cn('h-4 w-4', stat.color)} />
							</div>
						</CardHeader>
						<CardContent>
							{isLoading ? (
								<>
									<Skeleton className="h-8 w-16 mb-2" />
									<Skeleton className="h-4 w-24" />
								</>
							) : (
								<>
									<div className="text-xl sm:text-2xl font-bold">{stat.value}</div>
									<p className="text-xs text-muted-foreground mt-1">{stat.description}</p>
								</>
							)}
						</CardContent>
					</Card>
				))}
			</div>

			{/* Quick Actions - Mobile first */}
			<div className="grid gap-3 sm:gap-4 sm:grid-cols-2">
				<Card>
					<CardHeader>
						<CardTitle className="text-base sm:text-lg flex items-center gap-2">
							<Zap className="h-5 w-5 text-primary" />
							Azioni Rapide
						</CardTitle>
						<CardDescription>Operazioni frequenti</CardDescription>
					</CardHeader>
					<CardContent className="space-y-2">
						<Button asChild className="w-full" size="sm">
							<Link href="/dashboard/upload" className="flex items-center justify-center">
								<Upload className="mr-2 h-4 w-4" />
								Carica Documento
							</Link>
						</Button>
						<Button asChild variant="outline" className="w-full" size="sm">
							<Link href="/dashboard/search" className="flex items-center justify-center">
								<Search className="mr-2 h-4 w-4" />
								Chat AI
							</Link>
						</Button>
						<Button asChild variant="outline" className="w-full" size="sm">
							<Link href="/dashboard/documents" className="flex items-center justify-center">
								<FileText className="mr-2 h-4 w-4" />
								Visualizza Documenti
							</Link>
						</Button>
					</CardContent>
				</Card>

				<Card>
					<CardHeader>
						<CardTitle className="text-base sm:text-lg flex items-center gap-2">
							<TrendingUp className="h-5 w-5 text-primary" />
							Stato Sistema
						</CardTitle>
						<CardDescription>Monitoraggio servizi</CardDescription>
					</CardHeader>
					<CardContent>
						<div className="space-y-3">
							{systemStatus.map((item) => (
								<div
									key={item.name}
									className="flex items-center justify-between gap-2 p-2 rounded-lg"
								>
									<span className="text-xs sm:text-sm flex-1">{item.name}</span>
									<div className={cn('flex items-center gap-1.5', getStatusColor(item.status))}>
										{getStatusIcon(item.status)}
										<span className="text-xs sm:text-sm font-medium capitalize">
											{item.status === 'online' ? 'Online' : item.status === 'pending' ? 'In attesa' : 'Errore'}
										</span>
									</div>
								</div>
							))}
						</div>
					</CardContent>
				</Card>
			</div>

			{/* Recent Activity */}
			<Card>
				<CardHeader>
					<CardTitle className="text-base sm:text-lg flex items-center gap-2">
						<Activity className="h-5 w-5 text-primary" />
						Attività Recente
					</CardTitle>
					<CardDescription>Le ultime operazioni sui documenti</CardDescription>
				</CardHeader>
				<CardContent>
					{recentActivity.length === 0 ? (
						<div className="text-center py-12">
							<div className="relative inline-block mb-4">
								<div className="rounded-full bg-primary/10 p-4">
									<Activity className="h-8 w-8 text-primary" />
								</div>
							</div>
							<p className="text-sm text-muted-foreground mb-2">
								Nessuna attività recente
							</p>
							<p className="text-xs text-muted-foreground mb-4">
								Inizia caricando il tuo primo documento
							</p>
							<Button asChild variant="outline" size="sm">
								<Link href="/dashboard/upload" className="flex items-center">
									<Upload className="mr-2 h-4 w-4" />
									Carica il primo documento
								</Link>
							</Button>
						</div>
					) : (
						<div className="space-y-3">
							{recentActivity.map((activity) => (
								<div
									key={activity.id}
									className="flex items-start gap-3 p-3 border rounded-lg"
								>
									<div className="flex-shrink-0 mt-0.5 p-1.5 rounded-lg bg-primary/10">
										{activity.type === 'upload' && (
											<Upload className="h-4 w-4 text-primary" />
										)}
										{activity.type === 'process' && (
											<Activity className="h-4 w-4 text-primary" />
										)}
										{activity.type === 'search' && (
											<Search className="h-4 w-4 text-primary" />
										)}
									</div>
									<div className="flex-1 min-w-0">
										<p className="text-sm font-medium">{activity.description}</p>
										<p className="text-xs text-muted-foreground mt-1">
											{new Date(activity.timestamp).toLocaleString('it-IT')}
										</p>
									</div>
								</div>
							))}
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	)
}
