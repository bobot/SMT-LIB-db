const std = @import("std");
const fs = std.fs;
const print = std.debug.print;

const span = struct { start: usize, end: usize };

fn skip_to_level(str: []u8, start_idx: usize, start_level: usize, target_level: usize) ?usize {
    var level: usize = start_level;
    var idx = start_idx;

    var in_str: bool = false;
    var in_symb: bool = false;
    while (idx < str.len) {
        const chr = str[idx];
        switch (chr) {
            '|' => {
                if (in_str) break;
                in_symb = !in_symb;
            },
            '"' => {
                if (in_symb) break;
                in_str = !in_str;
            },
            '(' => {
                if (in_symb or in_str) break;
                level += 1;
                if (level == target_level)
                    return idx + 1;
            },
            ')' => {
                if (in_symb or in_str) break;
                // TODO: catch underflow error properly
                level -= 1;
                if (level == target_level)
                    return idx + 1;
            },
            else => {},
        }
        idx += 1;
    }
    return null;
}

fn get_command(str: []u8, start_idx: usize) span {
    var idx = start_idx;

    while (idx < str.len) {
        const char = str[idx];
        if (!(char == 9 or char == 10 or char == 13 or char == 32)) {
            break;
        }
        idx += 1;
    }
    const cmd_start = idx;
    while (idx < str.len) {
        const char = str[idx];
        if (char != '-' and (char < 'a' or char > 'z'))
            break;
        idx += 1;
    }
    return .{ .start = cmd_start, .end = idx };
}

pub fn main() !u8 {
    const stdout_file = std.io.getStdOut().writer();
    var bw = std.io.bufferedWriter(stdout_file);
    const stdout = bw.writer();

    if (.windows == @import("builtin").os.tag) {
        print("Windows is not supported.\n", .{});
        return 1;
    }

    if (std.os.argv.len < 2) {
        print("Klammerhammer -- Extract SMT-LIB metadata\n\n", .{});
        print("Usage:\n", .{});
        print("\tklhm FILENAME\n", .{});
        return 1;
    }

    const filename = std.mem.span(std.os.argv[1]);
    const file = try fs.cwd().openFile(filename, .{});
    defer file.close();

    const md = try file.metadata();
    const size = md.size();
    try stdout.print("File size: {}\n", .{size});
    const ptr = try std.os.mmap(
        null,
        md.size(),
        std.os.PROT.READ | std.os.PROT.WRITE,
        std.os.MAP.PRIVATE,
        file.handle,
        0,
    );
    defer std.os.munmap(ptr);

    var idx: usize = 0;
    while (idx < ptr.len) {
        idx = skip_to_level(ptr, idx, 0, 1) orelse break;

        const cmd = get_command(ptr, idx);
        try stdout.print("{s}\n", .{ptr[cmd.start..cmd.end]});
        try bw.flush(); // don't forget to flush!

        idx = skip_to_level(ptr, cmd.end, 1, 0) orelse break;
    }

    try bw.flush();

    return 0;
}
