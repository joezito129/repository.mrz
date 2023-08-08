from resources.lib.ui import maintenance, database_sync


database_sync.AnilistSyncDatabase()
maintenance.run_maintenance()
