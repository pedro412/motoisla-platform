export function isWebUsbSupported(): boolean {
  return typeof navigator !== "undefined" && "usb" in navigator;
}

export async function getAuthorizedDevices(): Promise<USBDevice[]> {
  if (!isWebUsbSupported()) return [];
  return navigator.usb.getDevices();
}

export async function requestDevice(): Promise<USBDevice> {
  return navigator.usb.requestDevice({ filters: [] });
}

export async function printViaUSB(data: Uint8Array): Promise<void> {
  const devices = await navigator.usb.getDevices();
  if (devices.length === 0) {
    throw new Error("No hay impresora USB autorizada. Conecta y autoriza la impresora primero.");
  }
  const device = devices[0];

  await device.open();
  try {
    if (device.configuration === null) {
      await device.selectConfiguration(1);
    }

    // Detect bulk-OUT endpoint dynamically — works with any ESC/POS compatible printer
    let interfaceNumber: number | null = null;
    let endpointNumber: number | null = null;

    outer: for (const iface of device.configuration!.interfaces) {
      for (const alternate of iface.alternates) {
        for (const endpoint of alternate.endpoints) {
          if (endpoint.direction === "out" && endpoint.type === "bulk") {
            interfaceNumber = iface.interfaceNumber;
            endpointNumber = endpoint.endpointNumber;
            break outer;
          }
        }
      }
    }

    if (interfaceNumber === null || endpointNumber === null) {
      throw new Error("No se encontró endpoint bulk-OUT en la impresora.");
    }

    await device.claimInterface(interfaceNumber);
    await device.transferOut(endpointNumber, data.buffer as ArrayBuffer);
    await device.releaseInterface(interfaceNumber);
  } finally {
    await device.close();
  }
}
