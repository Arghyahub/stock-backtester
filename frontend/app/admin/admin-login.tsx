"use client"
import React, { memo, useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import adminStore from '@/store/admin-store'
import Api from '@/utils/api/api'
import { Button } from '@/components/ui/button'


type Props = {}

const AdminLogin = (props: Props) => {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const setAdmin = adminStore(s => s.setAdmin);
  const is_admin = adminStore(s => s.is_admin);
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [loadingAuth, setLoadingAuth] = useState(true)

  useEffect(() => {
    const checkToken = async () => {
      const token = localStorage.getItem('token')
      if (!token) {
        setIsDialogOpen(true)
        setLoadingAuth(false)
        return
      }
    }

    checkToken()
  }, [])

  useEffect(() => {
    if (is_admin) {
      setLoadingAuth(false)
    }
  }, [is_admin])

  const handleLogin = async () => {
    try {
      const res = await Api.post(`/user/login`, {
        user_name: userName,
        password: password
      })

      if (res.status === 200) {
        if (res.access_token) {
          setAdmin(true,res.access_token)
          setIsDialogOpen(false)
        }
      } else {
        setAdmin(false)
      }
    } catch (e) {
      localStorage.removeItem('token')
    }
  }

  if (loadingAuth) {
    return <div className="p-4">Loading authentication...</div>
  }
  
  return (
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
  )
}

export default memo(AdminLogin)