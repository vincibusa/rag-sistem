'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Database, Package } from 'lucide-react'

export default function DatabasePage() {
	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight">Database Vettoriale</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Gestione del database vettoriale Qdrant
				</p>
			</div>

			<Card>
				<CardHeader>
					<CardTitle>Stato Database</CardTitle>
					<CardDescription>Informazioni sul database vettoriale</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="text-center py-12">
						<Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
						<p className="text-sm text-muted-foreground">
							Funzionalità in sviluppo
						</p>
					</div>
				</CardContent>
			</Card>
		</div>
	)
}
