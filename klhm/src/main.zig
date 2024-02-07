const std = @import("std");
const fs = std.fs;
const print = std.debug.print;

pub fn main() !u8{
    // stdout is for the actual output of your application, for example if you
    // are implementing gzip, then only the compressed bytes should be sent to
    // stdout, not any debugging messages.
    const stdout_file = std.io.getStdOut().writer();
    var bw = std.io.bufferedWriter(stdout_file);
    const stdout = bw.writer();

    if (.windows == @import("builtin").os.tag) {
        print("Windows is not supported.\n", .{});
        return 1;
    }

    if (std.os.argv.len < 2)
    {
        print("Klammerhammer -- Extract SMT-LIB metadata\n\n", .{});
        print("Usage:\n", .{});
        print("\tklhm FILENAME\n", .{});
        return 1;
    }
    std.debug.print("There are {d} args:\n", .{std.os.argv.len});
    for(std.os.argv) |arg| {
        std.debug.print("  {s}\n", .{arg});
    }

    const file = try fs.cwd().openFile(@as([]const u8, std.os.argv[1]), .{});
    defer file.close();

    const md = try file.metadata();
    const size = md.size();
    stdout.pring("File size: {}\n", .{size});
    const ptr = try std.os.mmap(
        null,
        md.size(),
        std.os.PROT.READ | std.os.PROT.WRITE,
        std.os.MAP.PRIVATE,
        file.handle,
        0,
    );
    defer std.os.munmap(ptr);

    // Manually increment idx to skip ahead if needed
    var idx : usize = 0;


    var sexpr : usize = 0;
    // Read file via mmap
    while (idx < size) {
        // What happens here:
        //    count ( ) to see where we are
        //    have ability to detect command
        //    have ability to ignore strings an ||

        const chr = ptr[idx];
        switch (chr) {
            '(' => {sexpr += 1;},
            ')' => {sexpr -= 1;},
            else => {}
        }
        print("level: {} {} {}\n", .{sexpr, chr, '('});

        idx += 1;
    }
    try bw.flush(); // don't forget to flush!

    return 0;
}

