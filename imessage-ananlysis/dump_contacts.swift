import Foundation
import Contacts

let store = CNContactStore()
let semaphore = DispatchSemaphore(value: 0)

let chatDB = NSString(string: "~/Library/Messages/chat.db").expandingTildeInPath
if !FileManager.default.isReadableFile(atPath: chatDB) {
    fputs("⚠️  Full Disk Access not granted — explore.py won't be able to read chat.db\n", stderr)
    fputs("   Grant it in: System Settings → Privacy & Security → Full Disk Access\n\n", stderr)
}

store.requestAccess(for: .contacts) { granted, error in
    guard granted else {
        fputs("ERROR: Contacts access denied. Grant in System Settings → Privacy → Contacts.\n", stderr)
        exit(1)
    }

    let keys: [CNKeyDescriptor] = [
        CNContactGivenNameKey as CNKeyDescriptor,
        CNContactFamilyNameKey as CNKeyDescriptor,
        CNContactPhoneNumbersKey as CNKeyDescriptor,
        CNContactEmailAddressesKey as CNKeyDescriptor,
    ]

    let request = CNContactFetchRequest(keysToFetch: keys)
    var entries: [[String: String]] = []

    do {
        try store.enumerateContacts(with: request) { contact, _ in
            let fullName = [contact.givenName, contact.familyName]
                .filter { !$0.isEmpty }
                .joined(separator: " ")
            guard !fullName.isEmpty else { return }

            for phone in contact.phoneNumbers {
                entries.append(["phone": phone.value.stringValue, "name": fullName])
            }
            for email in contact.emailAddresses {
                entries.append(["email": email.value as String, "name": fullName])
            }
        }

        let data = try JSONSerialization.data(withJSONObject: entries, options: .prettyPrinted)
        if let json = String(data: data, encoding: .utf8) {
            print(json)
        }
    } catch {
        fputs("ERROR: \(error.localizedDescription)\n", stderr)
        exit(1)
    }

    semaphore.signal()
}

semaphore.wait()
