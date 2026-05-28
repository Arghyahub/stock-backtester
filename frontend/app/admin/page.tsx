"use client"

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import Config from '@/utils/config/config'
import Api from '@/utils/api/api'

export default function AdminPage() {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [loadingAuth, setLoadingAuth] = useState(true)

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token')
      if (!token) {
        setIsDialogOpen(true)
        setLoadingAuth(false)
        return
      }

      try {
        const response = await fetch(`${Config.NEXT_PUBLIC_API_BASE_URL}/users/verify`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (response.status === 200) {
          setIsAuthenticated(true)
        } else {
          localStorage.removeItem('token')
          router.push('/home')
        }
      } catch (error) {
        localStorage.removeItem('token')
        router.push('/home')
      } finally {
        setLoadingAuth(false)
      }
    }

    verifyToken()
  }, [router])

  const handleLogin = async () => {
    try {
      const res = await Api.post(`/users/login`, {
        user_name: userName,
        password: password
      })

      if (res.status === 200) {
        if (res.access_token) {
          localStorage.setItem('token', res.access_token)
          setIsDialogOpen(false)
          setIsAuthenticated(true)
        }
      } else {
        localStorage.removeItem('token')
        router.push('/home')
      }
    } catch (e) {
      localStorage.removeItem('token')
      // router.push('/home')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setIsAuthenticated(false)
    router.push('/home')
  }

  if (loadingAuth) {
    return <div className="p-4">Loading authentication...</div>
  }

  return (
    <div className="relative min-h-screen p-8">
      {isAuthenticated && (
        <Button 
          variant="destructive" 
          onClick={handleLogout} 
          className="absolute top-4 right-4"
        >
          Logout
        </Button>
      )}

      <div>
        <h1 className="text-2xl font-bold">Admin Dashboard</h1>
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Admin Login</DialogTitle>
            <DialogDescription>
              Please enter your admin credentials to continue.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            <Input 
              placeholder="Username" 
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
            />
            <Input 
              type="password"
              placeholder="Password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button onClick={handleLogin}>Submit</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}