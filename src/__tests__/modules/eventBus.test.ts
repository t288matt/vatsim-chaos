import { describe, it, expect, vi } from 'vitest'
import { EventBus } from '../../modules/eventBus'

describe('EventBus', () => {
  describe('basic on() and emit()', () => {
    it('should call listener when event is emitted', () => {
      const eventBus = new EventBus()
      const listener = vi.fn()

      eventBus.on('test:event', listener)
      eventBus.emit('test:event', { value: 42 })

      expect(listener).toHaveBeenCalledOnce()
      expect(listener).toHaveBeenCalledWith({ value: 42 })
    })
  })

  describe('unsubscribe', () => {
    it('should unsubscribe using returned unsubscribe function', () => {
      const eventBus = new EventBus()
      const listener = vi.fn()

      const unsubscribe = eventBus.on('test:event', listener)
      eventBus.emit('test:event', { value: 1 })
      expect(listener).toHaveBeenCalledOnce()

      unsubscribe()
      eventBus.emit('test:event', { value: 2 })
      expect(listener).toHaveBeenCalledOnce() // Still only called once
    })

    it('should unsubscribe using off() method', () => {
      const eventBus = new EventBus()
      const listener = vi.fn()

      eventBus.on('test:event', listener)
      eventBus.emit('test:event', { value: 1 })
      expect(listener).toHaveBeenCalledOnce()

      eventBus.off('test:event', listener)
      eventBus.emit('test:event', { value: 2 })
      expect(listener).toHaveBeenCalledOnce() // Still only called once
    })
  })

  describe('multiple listeners', () => {
    it('should call all listeners on the same event', () => {
      const eventBus = new EventBus()
      const listener1 = vi.fn()
      const listener2 = vi.fn()

      eventBus.on('files:selected', listener1)
      eventBus.on('files:selected', listener2)

      const payload = { files: ['file1.ts', 'file2.ts'] }
      eventBus.emit('files:selected', payload)

      expect(listener1).toHaveBeenCalledOnce()
      expect(listener1).toHaveBeenCalledWith(payload)
      expect(listener2).toHaveBeenCalledOnce()
      expect(listener2).toHaveBeenCalledWith(payload)
    })

    it('should handle unsubscribe of one listener without affecting others', () => {
      const eventBus = new EventBus()
      const listener1 = vi.fn()
      const listener2 = vi.fn()

      eventBus.on('files:selected', listener1)
      eventBus.on('files:selected', listener2)
      eventBus.emit('files:selected', { files: ['a.ts'] })

      expect(listener1).toHaveBeenCalledOnce()
      expect(listener2).toHaveBeenCalledOnce()

      eventBus.off('files:selected', listener1)
      eventBus.emit('files:selected', { files: ['b.ts'] })

      expect(listener1).toHaveBeenCalledOnce() // Still only called once
      expect(listener2).toHaveBeenCalledTimes(2) // Called again
    })
  })
})
