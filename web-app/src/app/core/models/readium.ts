import { EpubNavigatorListeners, KeyboardPeripheralEventData } from '@readium/navigator';
import { Locator } from '@readium/shared';
import {
  BasicTextSelection,
  ContextMenuEvent,
  FrameClickEvent,
  SuspiciousActivityEvent
} from '@readium/navigator-html-injectables';

export const NOOP_EPUB_LISTENERS: EpubNavigatorListeners = {
  frameLoaded: (wnd: Window) => {
  },
  positionChanged: (locator: Locator) => {
  },
  tap: (e: FrameClickEvent) => {
    return true
  },
  click: (e: FrameClickEvent) => {
    return true
  },
  zoom: (scale: number) => {
  },
  miscPointer: (amount: number) => {
  },
  scroll: (delta: number) => {
  },
  customEvent: (key: string, data: unknown) => {
  },
  handleLocator: (locator: Locator) => {
    return true
  },
  textSelected: (selection: BasicTextSelection) => {
  },
  contentProtection: (type: string, data: SuspiciousActivityEvent) => {
  },
  contextMenu: (data: ContextMenuEvent) => {
  },
  peripheral: (data: KeyboardPeripheralEventData) => {
  }
}
