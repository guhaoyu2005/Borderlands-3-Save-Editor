import os
import sys
import OakSave_pb2

dk1 = bytearray([0x71, 0x34, 0x36, 0xB3, 0x56, 0x63, 0x25, 0x5F, 0xEA, 0xE2, 0x83, 0x73, 0xF4, 0x98, 0xB8, 0x18, 0x2E, 0xE5, 0x42, 0x2E, 0x50, 0xA2, 0x0F, 0x49, 0x87, 0x24, 0xE6, 0x65, 0x9A, 0xF0, 0x7C, 0xD7])
dk2 = bytearray([0x7C, 0x07, 0x69, 0x83, 0x31, 0x7E, 0x0C, 0x82, 0x5F, 0x2E, 0x36, 0x7F, 0x76, 0xB4, 0xA2, 0x71, 0x38, 0x2B, 0x6E, 0x87, 0x39, 0x05, 0x02, 0xC6, 0xCD, 0xD8, 0xB1, 0xCC, 0xA1, 0x33, 0xF9, 0xB6])


def write_u32_le(sc : bytearray, offset : int, val: int):
    sc[offset] = val & 0xFF
    sc[offset + 1] = (val >> 8) & 0xFF
    sc[offset + 2] = (val >> 16) & 0xFF 
    sc[offset + 3] = (val >> 24) & 0xFF

def read_u32_le(sc : bytearray, offset : int):
    ret = sc[offset]
    ret |= sc[offset + 1] << 8
    ret |= sc[offset + 2] << 16
    ret |= sc[offset + 3] << 24
    return ret

def find_save_core_offset(sc : bytearray):
    #core offset is always "OakSaveGame\0" + 4 bytes (<- this is the payload size)
    sc_str = "OakSaveGame"
    ret = -1
    for offset in range(0, len(sc) - len(sc_str)):
        match = True
        for i in range(0, len(sc_str)):
            if sc[offset + i] != ord(sc_str[i]):
                match = False
                break
        if match:
            ret = offset
            break

    if ret == -1:
        print("Cannot locate core offset")
        exit(-1)

    # skip the OakSaveGame string
    ret = ret + len(sc_str) + 1
    core_sz = read_u32_le(sc, ret)
    return ret, core_sz

def usage():
    print("Usage: python bdeh.py <save file>")


def decrypt(src : bytearray):
    offset = len(src) - 1
    while offset >= 0:
        k1 = 0
        if offset >= 0x20:
            k1 = src[offset - 0x20]
        else:
            k1 = dk1[offset]

        k2 = offset
        k2 = k2 % 0x20
        k2 = dk2[k2]
        k2 = k2 ^ k1

        src[offset] = int(src[offset]) ^ k2
        offset = offset - 1
    return src

def encrypt(src : bytearray):
    offset = 0
    while offset < len(src):
        if offset >= 0x20:
            k1 = src[offset - 0x20]
        else:
            k1 = dk1[offset]

        k2 = offset
        k2 = k2 % 0x20
        k2 = dk2[k2]
        k2 = k2 ^ k1

        src[offset] = int(src[offset]) ^ k2
        offset = offset + 1
    return src

def editor(save_obj):
    TYPE_INT = 0
    TYPE_FLOAT = 1
    TYPE_STRING = 2
    TYPE_DICT = 3
    TYPE_BOOL = 4
    TYPE_MS = 5 #MS_Complete or MS_Active

    vMap = {
        'save_game_id': {
            'func': save_obj.save_game_id,
            'type': TYPE_INT 
        },
        'last_save_timestamp': {
            'func': save_obj.last_save_timestamp,
            'type': TYPE_INT
        },
        'time_played_seconds': {
            'func': save_obj.time_played_seconds,
            'type': TYPE_INT
        },
        'player_class_data': {
            'func': save_obj.player_class_data,
            'type': TYPE_DICT
        },
        'resource_pools': {
            'func': save_obj.resource_pools,
            'type': TYPE_DICT
        },
        'saved_regions': {
            'func': save_obj.saved_regions,
            'type': TYPE_DICT
        },
        'experience_points': {
            'func': save_obj.experience_points,
            'type': TYPE_INT
        },
        'game_stats_data': {
            'func': save_obj.game_stats_data,
            'type': TYPE_DICT
        },
        'inventory_category_list': {
            'func': save_obj.inventory_category_list,
            'type': TYPE_DICT
        },
        'inventory_items': {
            'func': save_obj.inventory_items,
            'type': TYPE_DICT
        }
    }

    def show(vType):
        if vType in vMap:
            print("==========================\n")
            print(str(vType) + ": " + str(vMap[vType]['func']))
            print("==========================\n")
            return
        print("Error: " + str(vType) + " is not a valid value.")

    def show_cash():
        for i in vMap['inventory_category_list']['func']:
            if i.base_category_definition_hash == 618814354:
                print("Current cash: " + str(i.quantity))
                return
        print("Error: Cash category hash is not existing.")

    def update(vType, val):
        if vType in vMap:
            # add validation later
            tval = val
            if vMap[vType]['type'] == TYPE_INT:
                tval = int(val)
            elif vMap[vType]['type'] == TYPE_FLOAT:
                tval = float(val)

            vMap[vType]['func'] = tval
            print("Success.\n")
            return
        print("Error: " + str(vType) + " is not a valid value.")

    def update_cash(val):
        for i in range(0, len(vMap['inventory_category_list']['func'])):
            if vMap['inventory_category_list']['func'][i].base_category_definition_hash == 618814354:
                vMap['inventory_category_list']['func'][i].quantity = val
                print("Success.\n")
                return
        print("Error: Cash category hash is not existing.")

    def print_menu():
        print("BdEH: Save Editor for Borderland 3\n")
        print("Commands:\nhelp\nget\nset\nsaveexit\nexit\n")


    def command(input):
        #try:
            ele = input.split()
            cmd = ele[0]
            if cmd == 'get':
                if ele[1] == 'cash':
                    show_cash()
                else:
                    show(ele[1])
            elif cmd == 'set':
                if ele[1] == 'cash':
                    update_cash(int(ele[2]))
                else:
                    update(ele[1], ele[2])
            else:
                print("Error: Invalid command")
        #except:
        #    print("Error: Invalid command.")

    print_menu()
    while True:
        uin = input('Please input a command: ')
        if uin == 'saveexit':
            break
        elif uin == 'exit':
            exit()
        command(uin) 

    f = open('obj.txt', 'w')
    f.write(str(save_obj))
    f.close()
    return 

def main():
    if len(sys.argv) != 2:
        usage()
        exit()
    
    print("Reading " + sys.argv[1])
    with open(sys.argv[1], "rb") as f:
        savfile = f.read()
    
    core_offset, core_sz = find_save_core_offset(savfile)

    if core_offset + core_sz + 4 != len(savfile):
        print("Incorrect file size!")
        exit(1)

    print("Save file loaded - size: " + hex(len(savfile)) + " core offset: " + hex(core_offset) + " core size: " + hex(core_sz))

    # copy the payload
    payload = bytearray(core_sz)

    for i in range(0, core_sz):
        payload[i] = savfile[core_offset + 4 + i]

    # copy the header
    header = bytearray(core_offset)
    
    for i in range(0, core_offset):
        header[i] = savfile[i]

    # garbage collect the savfile buffer
    savfile = None

    # decrypt the payload
    payload = decrypt(payload)
    
    # deserialize the payload
    save_obj = OakSave_pb2.Character()
    save_obj.ParseFromString(payload)

    # editor loop
    editor(save_obj)

    # serialize the payload
    payload_ro = save_obj.SerializeToString()

    payload = bytearray(len(payload_ro))
    for i in range(0, len(payload_ro)):
        payload[i] = payload_ro[i]

    # encrypt the payload
    payload = encrypt(payload)

    # build the full save
    full_save = bytearray(core_offset + 4 + len(payload))
    for i in range(0, core_offset):
        full_save[i] = header[i]
    write_u32_le(full_save, core_offset, len(payload))
    for i in range(0, len(payload)):
        full_save[core_offset + 4 + i] = payload[i]

    # Write 
    with open(sys.argv[1] + ".bdeh", "wb") as f:
        f.write(full_save)

main()
